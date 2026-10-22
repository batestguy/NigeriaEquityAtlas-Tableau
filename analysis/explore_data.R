#!/usr/bin/env Rscript
# analysis/explore_data.R -- what data do we have, what does it say, and what
# could we test next?
#
# Reads the processed/interim/reference tables the nine-stage pipeline already
# produced and writes ONE self-contained HTML file:
#
#     analysis/data_explorer.html
#
# Self-contained means: every figure is a base64 PNG written into the page, and
# every table is plain HTML. No CDN, no pandoc, no network -- the file opens
# offline from a USB stick.
#
# It is NOT part of run_all.ps1. It is an exploration companion to the atlas:
# it invents no numbers, it re-reads the pipeline's outputs and, where it
# computes something new, it says so in the text.
#
# Usage:  Rscript analysis/explore_data.R        (from the repo root)
#         Rscript analysis/explore_data.R C:\path\to\repo

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
})

find_root <- function(start = getwd()) {
  d <- normalizePath(start, winslash = "/", mustWork = TRUE)
  for (i in 1:8) {
    if (file.exists(file.path(d, "AGENTS.md")) && dir.exists(file.path(d, "data"))) {
      return(d)
    }
    p <- dirname(d)
    if (identical(p, d)) break
    d <- p
  }
  stop("Could not find the repo root (the folder holding AGENTS.md and data/).")
}

args <- commandArgs(trailingOnly = TRUE)
ROOT <- if (length(args) >= 1) find_root(args[1]) else find_root()
OUT_DIR <- file.path(ROOT, "analysis")
dir.create(OUT_DIR, showWarnings = FALSE)
FIG_DIR <- file.path(tempdir(), "atlas_explorer_figs")
dir.create(FIG_DIR, showWarnings = FALSE)

RD <- function(...) read.csv(file.path(ROOT, ...), check.names = FALSE, stringsAsFactors = FALSE)

# ---------------------------------------------------------------------------
# Palettes -- kept identical to scripts/atlas_text.py so the explorer and the
# workbook cannot disagree about what dark red means.
# ---------------------------------------------------------------------------
BAND_COLS <- c(
  "1. under 5%"       = "#ffe5e5",
  "2. 5% to 10%"      = "#ffb8b8",
  "3. 10% to 20%"     = "#ff8a8a",
  "4. 20% to 30%"     = "#f45555",
  "5. 30% and above"  = "#d80000"
)
BAND_INK <- c(
  "1. under 5%" = "#8a5a5a", "2. 5% to 10%" = "#a33a3a", "3. 10% to 20%" = "#a33a3a",
  "4. 20% to 30%" = "#8f1f1f", "5. 30% and above" = "#7a0000"
)
SPATIAL_COLS <- c(
  "HH" = "#969696",  # poorer than average, neighbours poorer too
  "HL" = "#54278f",  # poorer than average, neighbours better off
  "LH" = "#80cdc1",  # better off than average, neighbours poorer
  "LL" = "#01665e"   # better off than average, neighbours better off
)
SPATIAL_WORDS <- c(
  HH = "Poorer than average, neighbours poorer too",
  HL = "Poorer than average, neighbours better off",
  LH = "Better off than average, neighbours poorer",
  LL = "Better off than average, neighbours better off"
)
INK <- "#1b2a33"
ACCENT <- "#0b6a8f"

TH <- theme_minimal(base_size = 11) +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(colour = "#e8edf0", linewidth = 0.3),
    plot.title = element_text(face = "bold", size = 12, colour = INK),
    plot.subtitle = element_text(size = 9.5, colour = "#5b6b75", margin = margin(b = 8)),
    plot.caption = element_text(size = 8.2, colour = "#7b8891", hjust = 0),
    axis.title = element_text(size = 9.5, colour = "#41525c"),
    axis.text = element_text(size = 8.8, colour = "#41525c"),
    legend.title = element_text(size = 9, colour = "#41525c"),
    legend.text = element_text(size = 8.6, colour = "#41525c"),
    legend.position = "bottom",
    plot.margin = margin(8, 12, 8, 8)
  )

band_fill <- function(reverse = TRUE) {
  scale_fill_manual(values = BAND_COLS, drop = FALSE,
                    guide = guide_legend(reverse = reverse, nrow = 1))
}

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
esc <- function(x) {
  x <- as.character(x)
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x
}

fnum <- function(x, d = 2) {
  vapply(x, function(v) {
    if (is.na(v)) return("--")
    formatC(as.numeric(v), format = "f", digits = d, big.mark = ",")
  }, "")
}

img_tag <- function(path, alt, note = NULL) {
  uri <- base64enc::dataURI(file = path, mime = "image/png")
  cap <- if (is.null(note)) "" else paste0('<figcaption>', note, "</figcaption>")
  paste0('<figure><img alt="', esc(alt), '" src="', uri, '">', cap, "</figure>")
}

save_fig <- function(plot, name, width = 9, height = 5.5) {
  f <- file.path(FIG_DIR, paste0(name, ".png"))
  ggsave(f, plot, width = width, height = height, dpi = 140, bg = "white",
         limitsize = FALSE)
  f
}

# A sortable table. Numeric columns carry data-v so the JS sorts numbers, not
# formatted strings ("1,234" would otherwise sort as text).
df_table <- function(df, digits = 2, cls = "tbl") {
  is_num <- vapply(df, is.numeric, TRUE)
  hdr <- paste0("<th>", esc(names(df)), "</th>", collapse = "")
  rows <- vapply(seq_len(nrow(df)), function(i) {
    cells <- vapply(seq_along(df), function(j) {
      v <- df[[j]][i]
      if (is_num[j]) {
        if (is.na(v)) return('<td class="num">--</td>')
        sprintf('<td class="num" data-v="%s">%s</td>', format(v, scientific = FALSE),
                formatC(v, format = "f", digits = digits, big.mark = ","))
      } else {
        sprintf("<td>%s</td>", esc(ifelse(is.na(v), "", v)))
      }
    }, "")
    paste0("<tr>", paste(cells, collapse = ""), "</tr>")
  }, "")
  paste0('<table class="', cls, ' sortable"><thead><tr>', hdr,
         "</tr></thead><tbody>", paste(rows, collapse = ""), "</tbody></table>")
}

stat_card <- function(value, label, sub = NULL) {
  paste0('<div class="card"><div class="cv">', value, '</div><div class="cl">', label,
         "</div>", if (!is.null(sub)) paste0('<div class="cs">', sub, "</div>") else "",
         "</div>")
}

# ---------------------------------------------------------------------------
# 1. Load everything the pipeline produced
# ---------------------------------------------------------------------------
atlas      <- RD("data/processed/mpi_atlas_2021.csv")
poly       <- RD("data/processed/mpi_polygons.csv")
spoly      <- RD("data/processed/spatial_polygons.csv")
spat       <- RD("data/processed/spatial_diagnostics.csv")
sglob      <- RD("data/processed/spatial_global.csv")
panel      <- RD("data/processed/mpi_trends_panel.csv")
pal_panel  <- RD("data/processed/party_alignment_panel.csv")
pal_res    <- RD("data/processed/party_alignment_result.csv")
pal_state  <- RD("data/processed/party_alignment_state.csv")
vint       <- RD("data/processed/atlas_vintages.csv")

headline   <- RD("data/interim/mpi_headline.csv")
dims       <- RD("data/interim/mpi_dimensions.csv")
seci       <- RD("data/interim/mpi_se_ci.csv")
trends     <- RD("data/interim/mpi_trends.csv")
harm       <- RD("data/interim/ophi_harmonised_changes.csv")
conf_sy    <- RD("data/interim/conflict_state_year.csv")
conf_ev    <- RD("data/interim/conflict_events_attributed.csv")
clim_sy    <- RD("data/interim/climate_state_year.csv")
clim_b     <- RD("data/interim/climate_baseline_1991_2020.csv")
wmeta      <- RD("data/interim/spatial_weights_meta.csv")
lookup     <- RD("data/reference/state_lookup.csv")
capitals   <- RD("data/reference/state_capitals.csv")
domparty   <- RD("data/reference/state_dominant_party.csv")
gov_events <- RD("data/reference/governorship_events.csv")
prov       <- RD("data/raw/_provenance.csv")

# ---------------------------------------------------------------------------
# 2. Derived quantities the narrative quotes. Every number below is computed
#    here, once, so the prose and the figures cannot drift apart.
# ---------------------------------------------------------------------------
atlas$band <- factor(atlas$mpi_band, levels = names(BAND_COLS))
atlas$mpi_pct <- atlas$mpi * 100
atlas$mpi_lo_pct <- atlas$mpi_ci_lo * 100
atlas$mpi_hi_pct <- atlas$mpi_ci_hi * 100
atlas$rel_se_pct <- atlas$mpi_se / atlas$mpi * 100
atlas$ci_half_pct <- (atlas$mpi_ci_hi - atlas$mpi_ci_lo) / 2 * 100
atlas$hc_pct <- atlas$headcount_ratio_pct

BAND_TABLE <- as.data.frame(table(atlas$band))
names(BAND_TABLE) <- c("band", "states")

o <- atlas[order(atlas$mpi), ]
ADJ_PAIRS <- nrow(o) - 1L
ADJ_SHARED <- sum(o$mpi_ci_lo[-1] <= o$mpi_ci_hi[-nrow(o)])
MED_REL_SE <- median(atlas$rel_se_pct)
MED_CI_HALF <- median(atlas$ci_half_pct)
MED_MPI <- median(atlas$mpi_pct)
TOP3 <- utils::tail(o[, c("state", "mpi_pct", "mpi_lo_pct", "mpi_hi_pct")], 3)
TOP3 <- TOP3[order(-TOP3$mpi_pct), ]

panel$poverty_group <- atlas$poverty_group[match(panel$state, atlas$state)]
med_by_round <- reshape(aggregate(mpi ~ survey_year + poverty_group, panel, median),
                        idvar = "survey_year", timevar = "poverty_group", direction = "wide")
sd_by_round <- reshape(aggregate(mpi ~ survey_year + poverty_group, panel, sd),
                       idvar = "survey_year", timevar = "poverty_group", direction = "wide")
rounds <- sort(unique(panel$survey_year))

w <- reshape(panel[, c("state", "survey_year", "mpi")], idvar = "state",
             timevar = "survey_year", direction = "wide")
PERSIST <- vapply(seq(2, ncol(w) - 1), function(i)
  cor(w[[i]], w[[i + 1]], method = "spearman"), 0)
names(PERSIST) <- paste0(rounds[-length(rounds)], "-", rounds[-1])

CONV_ALL <- coef(lm(dmpi_annual ~ mpi_t0, pal_panel))
CONV_P12 <- coef(lm(dmpi_annual ~ mpi_t0, pal_panel[pal_panel$poverty_group == "Poorest 12", ]))
CONV_O25 <- coef(lm(dmpi_annual ~ mpi_t0, pal_panel[pal_panel$poverty_group == "Other 25", ]))

C2021 <- conf_sy[conf_sy$year == 2021, ]
ZERO_2021 <- sum(C2021$events == 0)
ZERO_2021_POOR <- sum(C2021$events[atlas$pcode[match(C2021$pcode, atlas$pcode)] %in%
                                     atlas$pcode[atlas$poverty_group == "Poorest 12"]] == 0)
nat_conf <- aggregate(cbind(events, fatalities) ~ year, conf_sy, sum)
zero_by_year <- aggregate(events ~ year, conf_sy, function(z) sum(z == 0))
CONF_EVENTS_N <- nrow(conf_ev)
CONF_YEARS <- range(conf_sy$year)
FAT_2021 <- nat_conf$fatalities[nat_conf$year == 2021]

lagcor <- function(x, y) cor(x, y, method = "spearman")
RHO_LAT_MPI <- lagcor(atlas$lat, atlas$mpi)
RHO_LAT_PRECIP <- lagcor(atlas$lat, atlas$baseline_precip_mm)
RHO_PRECIP_MPI <- lagcor(atlas$baseline_precip_mm, atlas$mpi)
RHO_PARTIAL <- lagcor(resid(lm(mpi ~ lat, atlas)), resid(lm(baseline_precip_mm ~ lat, atlas)))
poor_states <- atlas[atlas$mpi > 0.2, ]
RHO_HL_LAT_POOR <- lagcor(poor_states$contrib_health_pct / poor_states$contrib_education_pct,
                          poor_states$lat)
N_POOR_02 <- nrow(poor_states)

HM <- lm(headcount_ratio_pct ~ mpi, atlas)
R2_H_MPI <- summary(HM)$r.squared
SLOPE_H_MPI <- unname(coef(HM)[2])
RHO_H_MPI <- lagcor(atlas$mpi, atlas$headcount_ratio_pct)

gv <- function(key) sglob$value[sglob$key == key]
MORAN_I <- gv("h1_global_i")
MORAN_I_LAT <- gv("h2_resid_i")
MORAN_I_FULL <- gv("ctx_full_i")
LISA_RAW <- sum(spat$lisa_p < 0.05)
LISA_BONF <- sum(spat$lisa_p_bonferroni < 0.05)
LISA_BY <- sum(spat$lisa_p_by < 0.05)
LISA_BONF_STATES <- spat$state[spat$lisa_p_bonferroni < 0.05]
QUAD_N <- as.data.frame(table(spat$spatial_quadrant))

dim_means <- aggregate(cbind(contrib_health_pct, contrib_education_pct,
                             contrib_living_standards_pct) ~ poverty_group, atlas, mean)

KM_VARS <- c("mpi", "headcount_ratio_pct", "intensity_pct", "contrib_health_pct",
             "contrib_education_pct", "contrib_living_standards_pct")
set.seed(20261018)
km <- kmeans(scale(atlas[, KM_VARS]), centers = 3, nstart = 100)
KM_SIZES <- km$size
KM_BSS <- km$betweenss / km$totss

CORR_VARS <- c("mpi", "headcount_ratio_pct", "intensity_pct", "lat",
               "baseline_precip_mm", "conflict_exposure_index", "contrib_health_pct",
               "contrib_education_pct", "contrib_living_standards_pct",
               "population_thousands")
CORR_LABELS <- c("MPI", "Headcount H (%)", "Intensity (%)", "Latitude",
                 "Baseline rainfall", "Conflict exposure (2021)", "Health share (%)",
                 "Education share (%)", "Living standards share (%)", "Population")
CM <- cor(atlas[, CORR_VARS], method = "spearman")

H1B <- pal_res[pal_res$kind == "primary", ]
PARTY_BETA <- H1B$beta
PARTY_LO <- H1B$ci_lo
PARTY_HI <- H1B$ci_hi
PARTY_P <- H1B$p_perm
PARTY_MDE <- H1B$mde
PARTY_N <- H1B$n

# ---------------------------------------------------------------------------
# 3. Figures
# ---------------------------------------------------------------------------
FIGS <- list()
atlas$statef <- stats::reorder(atlas$state, atlas$mpi_pct)

# F1 -- the headline: every state, with the interval the publisher gives it.
FIGS$state_ci <- save_fig(
  ggplot(atlas, aes(x = mpi_pct, y = statef)) +
    geom_segment(aes(x = mpi_lo_pct, xend = mpi_hi_pct, yend = statef),
                 colour = "#9aa7ae", linewidth = 0.75) +
    geom_point(aes(fill = band), shape = 21, size = 3.1,
               colour = "#4a5a63", stroke = 0.4) +
    band_fill() +
    labs(title = "MPI by state, with the publisher's 95% interval",
         subtitle = paste0("Percent of the index. The grey bar is OPHI's published interval; ",
                           "because every neighbour's interval overlaps the next state's,\n",
                           "the order down the axis is a display order, not a measured ranking. ",
                           "Data: OPHI/UNDP subnational MPI, 2021 (MICS)."),
         x = "MPI (% of the index)", y = NULL, fill = "MPI band",
         caption = paste0("Median relative standard error ", fnum(MED_REL_SE, 1),
                          "%; ", ADJ_SHARED, " of ", ADJ_PAIRS,
                          " adjacent rank pairs overlap at 95%.")) +
    TH, "f01_state_ci", 9, 8.6)

# F2 -- how much of each estimate is noise
y_se_max <- max(hist(atlas$rel_se_pct, breaks = seq(0, 40, by = 2.5), plot = FALSE)$counts)
FIGS$rel_se <- save_fig(
  ggplot(atlas, aes(x = rel_se_pct)) +
    geom_histogram(binwidth = 2.5, fill = "#ff8a8a", colour = "white", linewidth = 0.4) +
    geom_vline(xintercept = MED_REL_SE, colour = "#d80000", linewidth = 0.8, linetype = 2) +
    annotate("text", x = MED_REL_SE + 1.2, y = y_se_max * 0.97, vjust = 1, hjust = 0,
             label = paste0("median ", fnum(MED_REL_SE, 1), "%"), size = 3, colour = "#7a0000") +
    labs(title = "The noise floor: how big each state's standard error is, relative to its own MPI",
         subtitle = paste0("A median relative standard error of ", fnum(MED_REL_SE, 1),
                           "% means a state's true value could sit a seventh of a state apart from\n",
                           "the number printed for it. This is why the atlas colours bands and ",
                           "refuses to name a single poorest state."),
         x = "Relative standard error (standard error / MPI, %)", y = "States",
         caption = paste0("n = 37. Median published interval half-width ",
                          fnum(MED_CI_HALF, 1), " percentage points against a median MPI of ",
                          fnum(MED_MPI, 1), " points.")) +
    TH, "f02_rel_se", 8.4, 4.6)

# F3 -- headcount and index travel together
FIG_H <- lm(hc_pct ~ mpi_pct, atlas)
FIGS$h_vs_mpi <- save_fig(
  ggplot(atlas, aes(x = mpi_pct, y = hc_pct)) +
    geom_smooth(method = "lm", formula = y ~ x, colour = "#5b6b75",
                fill = "#dfe7ea", linewidth = 0.7, alpha = 0.6) +
    geom_point(aes(fill = band, size = intensity_pct), shape = 21,
               colour = "#4a5a63", stroke = 0.4) +
    scale_size_continuous(range = c(2, 7), name = "Intensity of\ndeprivation (%)") +
    band_fill() +
    labs(title = "The two ways of saying 'poor': headcount share against the MPI value",
         subtitle = paste0("Headcount H (share of people who are poor) and the MPI value ",
                           "(that share x how deprived they are, on average)\nare two views of the ",
                           "same 37 observations. Point size is intensity -- the multiplier between them."),
         x = "MPI (% of the index)", y = "Headcount ratio H (% of people)",
         fill = "MPI band",
         caption = paste0("Linear fit: H = ", fnum(unname(coef(FIG_H)[1]), 1), " + ",
                          fnum(unname(coef(FIG_H)[2]), 2), " x MPI, R-squared = ",
                          fnum(R2_H_MPI, 3), "; Spearman rho = ", fnum(RHO_H_MPI, 3), ".")) +
    TH, "f03_h_vs_mpi", 8.6, 5.4)

# F4 -- level over time, split by the poorest twelve against the rest
long <- rbind(
  data.frame(survey_year = panel$survey_year, mpi_pct = panel$mpi * 100,
             grp = "All 37 states", state = panel$state),
  data.frame(survey_year = panel$survey_year, mpi_pct = panel$mpi * 100,
             grp = panel$poverty_group, state = panel$state)
)
med <- aggregate(mpi_pct ~ survey_year + grp, long, median)
GRP_COLS <- c("All 37 states" = "#7b8891", "Poorest 12" = "#d80000", "Other 25" = "#0b6a8f")
FIGS$trend <- save_fig(
  ggplot(long, aes(x = survey_year, y = mpi_pct)) +
    geom_line(aes(group = interaction(state, grp)), colour = "#cdd6da",
              linewidth = 0.25, alpha = 0.55) +
    geom_line(data = med, aes(colour = grp), linewidth = 1.1) +
    geom_point(data = med, aes(colour = grp), size = 2.6) +
    scale_colour_manual(values = GRP_COLS, name = NULL) +
    scale_y_log10(breaks = c(3, 5, 8, 12, 20, 30, 45),
                  labels = function(z) paste0(z, "%")) +
    scale_x_continuous(breaks = rounds) +
    labs(title = "Four survey rounds: the level fell, the gap between the two groups did not close",
         subtitle = paste0("Log scale, so equal distances are equal proportions. Thin grey lines are ",
                           "individual states; thick lines are group medians.\nThe poorest twelve ",
                           "(median ", fnum(med_by_round[1, "mpi.Poorest 12"], 1), "% in ", rounds[1],
                           ") sit about six times the rest (", fnum(med_by_round[1, "mpi.Other 25"], 1),
                           "%) and stayed there."),
         x = "Survey round", y = "Median MPI (log scale)",
         caption = paste0("Rounds: 2013 DHS, 2016 MICS, 2018 DHS, 2021 MICS. ", rounds[1], " to ",
                          rounds[4], " median: poorest twelve ", fnum(med_by_round[1, "mpi.Poorest 12"], 1),
                          "% -> ", fnum(med_by_round[4, "mpi.Poorest 12"], 1), "%; other 25 ",
                          fnum(med_by_round[1, "mpi.Other 25"], 1), "% -> ",
                          fnum(med_by_round[4, "mpi.Other 25"], 1), "%.")) +
    TH, "f04_trend", 8.6, 5.6)

# F5 -- rank persistence, tile by tile
rk <- do.call(rbind, lapply(rounds, function(y) {
  s <- panel[panel$survey_year == y, c("state", "mpi")]
  s$rank <- rank(s$mpi, ties.method = "first")
  data.frame(state = s$state, survey_year = y, rank = s$rank, mpi_pct = s$mpi * 100)
}))
ordr <- atlas$state[order(atlas$mpi)]
rk$state <- factor(rk$state, levels = ordr)
FIGS$rank_heat <- save_fig(
  ggplot(rk, aes(x = factor(survey_year), y = state)) +
    geom_tile(aes(fill = rank), colour = "white", linewidth = 0.35) +
    geom_text(aes(label = rank), size = 1.9, colour = "#3a4a52") +
    scale_fill_gradient(low = "#d80000", high = "#fff0f0", name = "Rank\n(1 = poorest)",
                        breaks = c(1, 10, 20, 30, 37)) +
    scale_y_discrete(limits = rev(ordr)) +
    labs(title = "Who is poor hardly changes from round to round",
         subtitle = paste0("Rows are states, ordered by their 2021 MPI. Filled number is that state's ",
                           "rank in each round; dark red is the poorest.\nThe pattern is nearly ",
                           "vertical, which is the atlas's persistence finding restated as a picture."),
         x = NULL, y = NULL,
         caption = paste0("Spearman rank correlation between consecutive rounds: ",
                          paste(paste0(names(PERSIST), " = ", fnum(PERSIST, 3)), collapse = "; "),
                          ". Level fell; structure held.")) +
    TH + theme(panel.grid = element_blank(), legend.position = "right"), "f05_rank", 7.2, 8.6)

# F6 -- where the deprivations sit
dimlong <- rbind(
  data.frame(state = atlas$state, mpi = atlas$mpi,
             dim = "Health", share = atlas$contrib_health_pct),
  data.frame(state = atlas$state, mpi = atlas$mpi,
             dim = "Education", share = atlas$contrib_education_pct),
  data.frame(state = atlas$state, mpi = atlas$mpi,
             dim = "Living standards", share = atlas$contrib_living_standards_pct)
)
dimlong$dim <- factor(dimlong$dim, levels = c("Health", "Education", "Living standards"))
DIM_COLS <- c("Health" = "#8c2d19", "Education" = "#d9a441", "Living standards" = "#4a7c8c")
dim_ord <- atlas$state[order(atlas$mpi)]
FIGS$dim_stack <- save_fig(
  ggplot(dimlong, aes(x = factor(state, levels = dim_ord), y = share, fill = dim)) +
    geom_col(width = 0.82) +
    geom_hline(yintercept = 100 / 3, linetype = 2, colour = "#7b8891", linewidth = 0.5) +
    scale_fill_manual(values = DIM_COLS, name = NULL) +
    labs(title = "Living standards is the heaviest dimension in every state",
         subtitle = paste0("Each bar is one state's poverty split into the three MPI dimensions ",
                           "(shares of the index, summing to 100%). States run\npoorest first. ",
                           "The dashed line is an even three-way split; living standards sits above it ",
                           "everywhere, by a near-constant margin."),
         x = NULL, y = "Share of the state's MPI (%)",
         caption = paste0("Means: living standards ", fnum(dim_means$contrib_living_standards_pct[1], 1),
                          "%, education ", fnum(dim_means$contrib_education_pct[1], 1), "%, health ",
                          fnum(dim_means$contrib_health_pct[1], 1), "%. Health rests on child mortality ",
                          "alone (nutrition is missing for all 37), so the health slice is not ",
                          "comparable with another country's.")) +
    TH + theme(axis.text.x = element_text(angle = 90, hjust = 1, size = 7.6)),
  "f06_dim_stack", 9, 5.6)

# @@APPEND@@



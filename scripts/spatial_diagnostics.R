# Stage 09 (R half) -- spatial diagnostics for the state poverty map.
#
# Implements exactly the specification frozen in docs/spatial_preregistration.md:
# Moran's I of the poverty score under queen contiguity, the same statistic on the
# residuals of  mpi ~ lat  (H2, the only version that is not already the
# north-south gradient), and the 37 local statistics with a Bonferroni correction
# across them (H3). Weights, seed, permutation count and the sensitivity set are
# fixed there and not chosen here.
#
# Why R: this pipeline's Python has no libpysal/esda, and spdep + spatialreg are
# installed and are the reference implementations. Stage 09's Python half runs
# this file with Rscript, then validates and labels the output.
#
# Reads  (from the repository root, given as the first argument):
#   data/raw/nga_adm1.geojson            the RAW geoBoundaries ADM1 file, so the
#                                        neighbour graph is built from the real
#                                        borders and not from the simplified rings
#   data/processed/mpi_atlas_2021.csv    37 states: mpi, lat, conflict, climate
#
# Writes (data/interim, all machine-readable; Python adds the reader words):
#   spatial_diagnostics.csv     37 rows: lag, quadrant code, local statistic, p
#   spatial_global.csv          the global statistics, one row per statistic
#   spatial_weights_meta.csv    the weight-matrix checks and the run settings
#
# No prose and no colours are written here. Nothing in this file decides what may
# be claimed -- the registration already did that.

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) args[[1]] else "."

suppressMessages({
  library(sf)
  library(spdep)
  library(spatialreg)
})

SEED <- 20261018L
NSIM <- 9999L
QUEEN_ONLY <- TRUE

geo_path <- file.path(root, "data", "raw", "nga_adm1.geojson")
atlas_path <- file.path(root, "data", "processed", "mpi_atlas_2021.csv")
out_dir <- file.path(root, "data", "interim")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

## ---------------------------------------------------------------- inputs
stopifnot(file.exists(geo_path), file.exists(atlas_path))

g <- st_read(geo_path, quiet = TRUE)
a <- read.csv(atlas_path, stringsAsFactors = FALSE)

# Join on the ISO code, never on a name. The atlas's own spelling wins: the
# gazetteer is the geometry source, not the naming source.
stopifnot(nrow(g) == 37L, nrow(a) == 37L)
stopifnot(!anyDuplicated(a[["pcode"]]))
idx <- match(a[["pcode"]], g[["shapeISO"]])
stopifnot("every atlas pcode must match exactly one ADM1 feature" = !anyNA(idx))

m <- g[idx, ]
stopifnot(identical(as.character(m[["shapeISO"]]), as.character(a[["pcode"]])))
stopifnot("no empty geometry" = !any(st_is_empty(m)))

m[["state"]] <- a[["state"]]
m[["mpi"]] <- a[["mpi"]]
m[["lat"]] <- a[["lat"]]
m[["conflict"]] <- a[["conflict_exposure_index"]]
m[["precip_anom"]] <- a[["precip_anomaly_pct"]]

## ------------------------------------------------- weights and their checks
nq <- poly2nb(m, queen = TRUE)
nr <- poly2nb(m, queen = FALSE)
cards <- card(nq)

stopifnot("a state with no neighbour would silently drop out of every statistic" =
            all(cards > 0))
stopifnot("the neighbour graph must be one connected component" =
            n.comp.nb(nq)$nc == 1L)

lw <- nb2listw(nq, style = "W")
lwr <- nb2listw(nr, style = "W")

# k = 4 nearest neighbours, by centroid distance: the pre-declared robustness
# check that the result is not an artefact of how "neighbour" is defined.
suppressWarnings(co <- st_coordinates(st_centroid(m)))
kn <- knn2nb(knearneigh(co, k = 4L))
lwk <- nb2listw(kn, style = "W")

queen_equals_rook <- identical(
  lapply(nq, sort), lapply(nr, sort)
)

## ------------------------------------------------------------------ H1
set.seed(SEED); mc <- moran.mc(m[["mpi"]], lw, nsim = NSIM)
mt <- moran.test(m[["mpi"]], lw)
i_mpi <- unname(mc$statistic)
p_mpi <- mc$p.value
var_i <- unname(mt$estimate[["Variance"]])

## ------------------------------------------- H2: after the north-south slope
r_lat <- lm(mpi ~ lat, data = m)
r_full <- lm(mpi ~ lat + conflict + precip_anom, data = m)
set.seed(SEED); mc_lat <- moran.mc(residuals(r_lat), lw, nsim = NSIM)
set.seed(SEED); mc_full <- moran.mc(residuals(r_full), lw, nsim = NSIM)
set.seed(SEED); mc_lat_hat <- moran.mc(m[["lat"]], lw, nsim = NSIM)
i_lat <- unname(mc_lat$statistic)
p_lat <- mc_lat$p.value
i_full <- unname(mc_full$statistic)
p_full <- mc_full$p.value

## ----------------------------------------------------- H3: the local tests
loc <- localmoran(m[["mpi"]], lw)
p_local <- loc[, ncol(loc)]                      # last column: unchanged across spdep versions
p_bonf <- p.adjust(p_local, method = "bonferroni")
p_by <- p.adjust(p_local, method = "BY")         # valid under spatial dependence
n_local_raw <- sum(p_local < 0.05)
n_local_bonf <- sum(p_bonf < 0.05)
n_local_by <- sum(p_by < 0.05)

## ------------------------------------------------------------- sensitivities
set.seed(SEED); mc_rook <- moran.mc(m[["mpi"]], lwr, nsim = NSIM)
i_rook <- unname(mc_rook$statistic); p_rook <- mc_rook$p.value
set.seed(SEED); mc_knn <- moran.mc(m[["mpi"]], lwk, nsim = NSIM)
i_knn <- unname(mc_knn$statistic); p_knn <- mc_knn$p.value
loc_knn <- localmoran(m[["mpi"]], lwk)
p_local_knn <- loc_knn[, ncol(loc_knn)]
n_local_knn_bonf <- sum(p.adjust(p_local_knn, method = "bonferroni") < 0.05)

# FCT out: no elected governor and a tiny, entirely urban polygon, so both the
# party test and every other state comparison in this atlas exclude it.
drop_fct <- which(m[["shapeISO"]] == "NG-FC")
stopifnot("FCT must be present in the atlas" = length(drop_fct) == 1L)
m_no <- m[-drop_fct, ]
nq_no <- poly2nb(m_no, queen = QUEEN_ONLY)
lw_no <- nb2listw(nq_no, style = "W")
stopifnot(all(card(nq_no) > 0))
set.seed(SEED); mc_no <- moran.mc(m_no[["mpi"]], lw_no, nsim = NSIM)
i_no_fct <- unname(mc_no$statistic)
p_no_fct <- mc_no$p.value

# Does a spatial error term buy anything over plain latitude? Reported, never
# used as a decision.
aic_ols <- AIC(r_lat)
aic_err <- AIC(errorsarlm(mpi ~ lat, data = m, listw = lw, quiet = TRUE))

## ------------------------------------------------------------------ output
z <- m[["mpi"]] - mean(m[["mpi"]])
lag_z <- lag.listw(lw, z)
lag_mpi <- mean(m[["mpi"]]) + lag_z
quadrant <- ifelse(z > 0 & lag_z > 0, "HH",
             ifelse(z > 0 & lag_z <= 0, "HL",
              ifelse(z <= 0 & lag_z > 0, "LH", "LL")))

per_state <- data.frame(
  pcode = m[["shapeISO"]],
  state = m[["state"]],
  lat = m[["lat"]],
  mpi = m[["mpi"]],
  neighbours = cards,
  spatial_lag_mpi = round(lag_mpi, 6),
  spatial_quadrant = quadrant,
  lisa_i = round(loc[, 1], 6),
  lisa_z = round(loc[, ncol(loc) - 1L], 6),
  lisa_p = signif(p_local, 6),
  lisa_p_bonferroni = signif(p_bonf, 6),
  lisa_p_by = signif(p_by, 6),
  stringsAsFactors = FALSE
)
stopifnot(nrow(per_state) == 37L, !anyNA(per_state[["spatial_lag_mpi"]]))

bonf_names <- m[["state"]][p_bonf < 0.05]
raw_names <- m[["state"]][p_local < 0.05]

# Eight significant digits: enough that stage 9's independent Python recomputation
# can be compared against these values tightly, instead of both being rounded to a
# display precision where a real disagreement would hide. Display formatting is the
# reader's, and lives in the Python half.
fmt <- function(x) format(signif(x, 8), scientific = FALSE, trim = TRUE)

global <- data.frame(
  key = c("h1_global_i", "h2_resid_i", "h3_survivors_n",
          "ctx_lat_i", "ctx_lat_r2", "ctx_full_i", "ctx_raw_n", "ctx_var",
          "ctx_delta_aic",
          "sen_rook_i", "sen_knn_i", "sen_no_fct_i", "sen_knn_survivors_n",
          "sen_by_survivors_n"),
  kind = c("H1", "H2", "H3",
           "context", "context", "context", "context", "context", "context",
           "sensitivity", "sensitivity", "sensitivity", "sensitivity", "sensitivity"),
  short = c(
    "Moran's I of the poverty score (queen contiguity)",
    "Moran's I after accounting for how far north a state is",
    "states whose own neighbourhood stands out after correcting for 37 tests",
    "Moran's I of how far north a state is",
    "share of the pattern explained by how far north a state is",
    "Moran's I after accounting for latitude plus conflict and climate",
    "states that look local before correcting for 37 tests",
    "variance of Moran's I under the null",
    "spatial-error model AIC minus ordinary-least-squares AIC",
    "queen weights replaced by rook weights",
    "queen weights replaced by the 4 nearest neighbours",
    "the 36 states with FCT excluded",
    "states surviving correction with the 4 nearest neighbours",
    "states surviving Benjamini-Yekutieli instead of Bonferroni"),
  statistic = c("morans_I", "morans_I", "n_states",
                "morans_I", "r_squared", "morans_I", "n_states", "variance", "delta_aic",
                "morans_I", "morans_I", "morans_I", "n_states", "n_states"),
  value = c(fmt(i_mpi), fmt(i_lat), as.character(n_local_bonf),
            fmt(unname(mc_lat_hat$statistic)),
            fmt(summary(r_lat)$r.squared), fmt(i_full), as.character(n_local_raw),
            fmt(var_i), fmt(aic_err - aic_ols),
            fmt(i_rook), fmt(i_knn), fmt(i_no_fct),
            as.character(n_local_knn_bonf), as.character(n_local_by)),
  p = c(fmt(p_mpi), fmt(p_lat), "",
        fmt(mc_lat_hat$p.value), "", fmt(p_full), "", "", "",
        fmt(p_rook), fmt(p_knn), fmt(p_no_fct), "", ""),
  nsim = c(rep(as.character(NSIM), 2), "", as.character(NSIM), "", as.character(NSIM),
           "", "", "", as.character(NSIM), as.character(NSIM), as.character(NSIM), "", ""),
  n = c(rep("37", 2), "37", "37", "37", "37", "37", "37", "37",
        "37", "37", "36", "37", "37"),
  note = c("", "", paste(bonf_names, collapse = "; "),
           "", "", "", paste(raw_names, collapse = "; "), "", "",
           "", "", "", "", ""),
  stringsAsFactors = FALSE
)

meta <- data.frame(
  metric = c("seed", "permutations", "geojson", "atlas", "n_units",
             "components", "units_without_a_neighbour",
             "neighbours_min", "neighbours_q1", "neighbours_median",
             "neighbours_mean", "neighbours_q3", "neighbours_max",
             "queen_equals_rook", "single_neighbour_states", "weighting", "knn_k"),
  value = c(as.character(SEED), as.character(NSIM),
            "data/raw/nga_adm1.geojson", "data/processed/mpi_atlas_2021.csv",
            as.character(nrow(m)), as.character(n.comp.nb(nq)$nc),
            as.character(sum(cards == 0)),
            fmt(min(cards)), fmt(as.numeric(quantile(cards, 0.25))), fmt(median(cards)),
            fmt(mean(cards)), fmt(as.numeric(quantile(cards, 0.75))), fmt(max(cards)),
            if (queen_equals_rook) "TRUE" else "FALSE",
            paste(m[["state"]][cards == min(cards)], collapse = "; "),
            "row-standardised", "4"),
  stringsAsFactors = FALSE
)

write.csv(per_state, file.path(out_dir, "spatial_diagnostics.csv"),
          row.names = FALSE, quote = FALSE)
write.csv(global, file.path(out_dir, "spatial_global.csv"),
          row.names = FALSE, quote = FALSE)
write.csv(meta, file.path(out_dir, "spatial_weights_meta.csv"),
          row.names = FALSE, quote = FALSE)

cat(sprintf("spatial diagnostics: I %.4f (p %s) | after latitude %.4f (p %s)\n",
            i_mpi, fmt(p_mpi), i_lat, fmt(p_lat)))
cat(sprintf("local: %d of 37 raw, %d after Bonferroni (%s), %d after BY\n",
            n_local_raw, n_local_bonf, paste(bonf_names, collapse = ", "), n_local_by))
cat(sprintf("neighbours: min %d, median %s, max %d; queen == rook: %s\n",
            min(cards), median(cards), max(cards), queen_equals_rook))

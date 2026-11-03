# Second page of app that contains the analysis of campaigns over time

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import map_vis


st.title("Year Over Year Analysis")

# TODO: switch to "campaign_id" when the SQL query is updated
SAMPLE_CAMPAIGN_COL = "organization_campaign_id"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def filter_to_matches(samples_gdf, matches, campaign_col=SAMPLE_CAMPAIGN_COL):
    """Return only the samples whose (campaign, field) pair appears in matches."""
    keys = (
        matches[["campaign_id", "field_id"]]
        .dropna()
        .drop_duplicates()
        .astype(str)
        .rename(columns={"campaign_id": "_cid", "field_id": "_fid"})
    )

    s = samples_gdf.copy()
    # Compare as strings so int vs str IDs still match
    s["_cid"] = s[campaign_col].astype(str)
    s["_fid"] = s["field_id"].astype(str)

    out = s.merge(keys, on=["_cid", "_fid"], how="inner").drop(columns=["_cid", "_fid"])
    return gpd.GeoDataFrame(out, geometry="geometry", crs=samples_gdf.crs)


def filter_fields_to_matches(fields_gdf, matches):
    """Return only the field boundaries whose (campaign, field) pair appears in matches."""
    keep = set(zip(matches["campaign_id"].astype(str), matches["field_id"].astype(str)))
    mask = [
        (str(c), str(f)) in keep
        for c, f in zip(fields_gdf["campaign_id"], fields_gdf["field_id"])
    ]
    return fields_gdf[mask]


def campaign_names(fields_gdf):
    """Map campaign_id (as str) -> campaign_name."""
    return dict(zip(fields_gdf["campaign_id"].astype(str), fields_gdf["campaign_name"].astype(str)))


def depth_labels(depth_values):
    """Map each sample_depth value in the data to a label like '0-15 cm', in depth order.

    Numeric depths are treated as the bottom of each layer, so 15 and 30 become
    '0-15 cm' and '15-30 cm'. Text depths (e.g. '0-15') are used as they are.
    """
    vals = pd.Series(pd.unique(pd.Series(depth_values).dropna()))
    num = pd.to_numeric(vals, errors="coerce")

    if num.notna().all():
        labels, top = {}, 0.0
        for i in num.sort_values().index:
            bottom = float(num[i])
            labels[vals[i]] = f"{top:g}-{bottom:g} cm"
            top = bottom
        return labels

    return {v: (str(v) if "cm" in str(v) else f"{v} cm") for v in sorted(vals, key=str)}


def campaign_acres(samples, campaign_col=SAMPLE_CAMPAIGN_COL):
    """Acres per campaign from the samples table, counting each field once.

    Each sample row carries its field's acres, so take one value per field
    rather than adding it once per sample. Ground sampled in more than one
    year is counted in each year it was sampled.
    """
    s = pd.DataFrame(samples.drop(columns="geometry"))
    s["campaign_id"] = s[campaign_col].astype(str)
    s["field_id"] = s["field_id"].astype(str)

    per_field = s.groupby(["campaign_id", "field_id"])["acres"].first()
    return per_field.groupby("campaign_id").sum().rename("Number of Acres")


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------

def summary_table(depth_samples, fields_gdf, matches, campaign_col=SAMPLE_CAMPAIGN_COL):
    """Number of samples and acres per campaign for one depth, plus a total row.

    depth_samples should already be filtered to matches and to the selected depth.
    """
    s = pd.DataFrame(depth_samples.drop(columns="geometry"))
    s["campaign_id"] = s[campaign_col].astype(str)

    samples = s.groupby("campaign_id")["total_carbon_pct"].count().rename("Number of Samples")
    acres = campaign_acres(depth_samples, campaign_col)

    # Keep every matched campaign, even one with no samples at this depth
    all_ids = sorted(matches["campaign_id"].astype(str).unique())
    out = pd.concat([samples, acres], axis=1).reindex(all_ids, fill_value=0)
    out.index.name = "campaign_id"
    out = out.reset_index()

    names = campaign_names(fields_gdf)
    out.insert(0, "Campaign Name", out["campaign_id"].map(names).fillna(out["campaign_id"]))

    # Total across years: ground sampled in more than one year counts once per year
    total = out[["Number of Samples", "Number of Acres"]].sum().to_frame().T
    total["Campaign Name"] = "Total (all years)"
    total["campaign_id"] = "Total"
    out = pd.concat([out, total], ignore_index=True)

    out["Number of Samples"] = out["Number of Samples"].astype(int)
    out["Number of Acres"] = out["Number of Acres"].round(2)
    
    return out.drop(columns="campaign_id")


def carbon_stats(matched_samples, campaign_col=SAMPLE_CAMPAIGN_COL):
    """Total carbon stats per campaign per depth (used for the executive summary)."""
    s = pd.DataFrame(matched_samples.drop(columns="geometry"))
    s[campaign_col] = s[campaign_col].astype(str)
    return (
        s.groupby([campaign_col, "sample_depth"])["total_carbon_pct"]
        .agg(["count", "mean", "std", "min", "max"])
        .reset_index()
        .rename(columns={campaign_col: "campaign_id"})
    )


# ---------------------------------------------------------------------------
# Change on the overlapping area
# ---------------------------------------------------------------------------

def clip_to_overlap(matched_samples, fields_gdf, matches, base, latest,
                    campaign_col=SAMPLE_CAMPAIGN_COL):
    """Keep base and latest samples that fall inside the area both campaigns covered."""
    f = filter_fields_to_matches(fields_gdf, matches)

    def area(cid):
        geoms = f[f["campaign_id"].astype(str) == str(cid)].geometry
        # use .unary_union instead on geopandas < 1.0
        return geoms.union_all()

    overlap = area(base).intersection(area(latest))

    s = matched_samples[matched_samples[campaign_col].astype(str).isin([str(base), str(latest)])]
    if s.crs != f.crs:
        s = s.to_crs(f.crs)
    return s[s.within(overlap)], overlap


def change_summary(overlap_samples, base, latest, names, labels, campaign_col=SAMPLE_CAMPAIGN_COL):
    """Mean total C per depth for base and latest on the overlap, plus the change."""
    s = pd.DataFrame(overlap_samples.drop(columns="geometry"))
    s[campaign_col] = s[campaign_col].astype(str)
    base, latest = str(base), str(latest)

    means = s.pivot_table(
        index="sample_depth",
        columns=campaign_col,
        values="total_carbon_pct",
        aggfunc="mean",
    )
    # A campaign with no samples inside the overlap gets an empty column
    for cid in (base, latest):
        if cid not in means.columns:
            means[cid] = float("nan")

    # Order rows by depth, the same order as the dropdown
    means = means.reindex([d for d in labels if d in means.index])

    out = pd.DataFrame(index=means.index)
    out[f"{names.get(base, base)} Mean C (%)"] = means[base]
    out[f"{names.get(latest, latest)} Mean C (%)"] = means[latest]
    out["Change (% pts)"] = means[latest] - means[base]

    out = out.reset_index()
    out.insert(0, "Depth", out["sample_depth"].map(labels))
    return out.drop(columns="sample_depth").round(3)


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------

def heat_maps(depth_samples, fields_gdf, matches, ssurgo_polys, campaign_col=SAMPLE_CAMPAIGN_COL):
    """depth_samples should already be filtered to matches and to one depth."""
    fields_gdf = filter_fields_to_matches(fields_gdf, matches)

    campaign_ids = sorted(matches["campaign_id"].unique())
    if not campaign_ids:
        st.info("No matched fields to map.")
        return

    names = campaign_names(fields_gdf)
    label = lambda cid: names.get(str(cid), str(cid))

    # One fixed carbon scale for every map, from the samples actually shown
    vals = depth_samples["total_carbon_pct"].dropna().astype(float)
    if vals.empty:
        st.info("No samples at this depth to map.")
        return
    vmin, vmax = float(vals.min()), float(vals.max())

    base, latest = campaign_ids[0], campaign_ids[-1]
    samples_for = lambda cid: depth_samples[depth_samples[campaign_col].astype(str) == str(cid)]
    fields_for = lambda cid: fields_gdf[fields_gdf["campaign_id"].astype(str) == str(cid)]

    cols = st.columns(len(campaign_ids) + (1 if len(campaign_ids) >= 2 else 0))

    for col, cid in zip(cols, campaign_ids):
        with col:
            st.markdown(f"**{label(cid)}**")
            m = map_vis.create_heat_map(
                samples_for(cid),
                fields_for(cid),
                matches[matches["campaign_id"] == cid],
                ssurgo_polys,
                vmin,
                vmax,
                label=label(cid),
                # Baseline is dashed white, every later campaign solid black,
                # matching how they appear on the change map
                style=map_vis.STYLE_A if cid == base else map_vis.STYLE_B,
            )
            st_folium(m, height=450, use_container_width=True,
                      key=f"heat_map_{cid}", returned_objects=[])
            st.markdown(map_vis.legend_html(vmin, vmax), unsafe_allow_html=True)

    if len(campaign_ids) >= 2:
        with cols[-1]:
            st.markdown(f"**Change: {label(base)} → {label(latest)}**")
            m, lim = map_vis.create_change_map(
                samples_for(base),
                samples_for(latest),
                fields_for(base),
                fields_for(latest),
                SSURGO=ssurgo_polys,
                label_a=label(base),
                label_b=label(latest),
            )
            st_folium(m, height=450, use_container_width=True,
                      key=f"change_map_{base}_{latest}", returned_objects=[])
            st.markdown(
                map_vis.legend_html(-lim, lim, colors=map_vis.CHANGE_COLORS,
                                    caption="Change in Total Carbon (% points)"),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def executive_summary(stats, change_table, names, labels, campaign_ids, org_name):
    first = names.get(str(campaign_ids[0]), str(campaign_ids[0]))
    last = names.get(str(campaign_ids[-1]), str(campaign_ids[-1]))

    total_samples = int(stats["count"].sum())
    depth_text = " and ".join(labels.values())
    c_min, c_max = stats["min"].min(), stats["max"].max()

    text = (
        f"The contents of this report provide an analysis of total carbon measured across "
        f"{first} and {last}. The objective of this study is to see how total carbon has changed "
        f"over time. "  # TODO: add the time between campaigns once sample dates are in the query
        f"{org_name} undertook soil sampling campaigns, collecting {total_samples} samples at "
        f"depths of {depth_text}. Samples were tested in a lab for total carbon. "
        f"Results indicate that total soil carbon content ranged from {c_min:.2f}% to {c_max:.2f}%. "
    )

    if change_table is not None and not change_table.empty:
        parts = [
            f"{row['Change (% pts)']:+.2f} percentage points at {row['Depth']}"
            for _, row in change_table.iterrows()
            if pd.notna(row["Change (% pts)"])
        ]
        if parts:
            text += (
                f"On the area sampled in both campaigns, mean total carbon changed by "
                f"{'; '.join(parts)}. "
            )

    text += (
        f"Using the Soil Survey Geographic Database (SSURGO) to estimate bulk density on the farm, "
        f"carbon stocks were calculated for {org_name} [1]. "
        # TODO: add C/acre averages once stock calculation is in place
        f"Carbon stock estimates ranged from "
    )
    return text


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

matches = st.session_state.get("matches")
samples_gdf = st.session_state.get("samples_gdf")
fields_gdf = st.session_state.get("fields_gdf")
ssurgo_polys = st.session_state.get("ssurgo_polys")

if matches is None or matches.empty or samples_gdf is None or fields_gdf is None:
    st.warning("Confirm matches on the Home page first.")
    st.stop()

matched_samples = filter_to_matches(samples_gdf, matches)
if matched_samples.empty:
    st.warning("None of the samples belong to the matched fields.")
    st.stop()

campaign_ids = sorted(matches["campaign_id"].unique())
names = campaign_names(fields_gdf)
org_name = samples_gdf["organization"].unique()[0]

# Depths come from the data, in order (e.g. 0-15 cm, 15-30 cm)
labels = depth_labels(matched_samples["sample_depth"])
depth = st.selectbox("Depth", list(labels.keys()), format_func=labels.get)
depth_label = labels[depth]
depth_samples = matched_samples[matched_samples["sample_depth"] == depth]

# Summary table: samples and acres for the selected depth only
st.subheader(f"Summary of Campaigns for {depth_label}")
st.data_editor(summary_table(depth_samples, fields_gdf, matches), hide_index=True)
st.caption("Total acres add each year's sampled area, so ground sampled in more than one year is counted once per year.")

# Maps
heat_maps(depth_samples, fields_gdf, matches, ssurgo_polys)
st.caption(f"Inverse Distance Weighted Interpolation {depth_label} total carbon %", text_alignment="center")

# Change on overlapping area
change_table = None
if len(campaign_ids) >= 2:
    base, latest = campaign_ids[0], campaign_ids[-1]
    overlap_samples, overlap = clip_to_overlap(matched_samples, fields_gdf, matches, base, latest)

    st.subheader("Change on Area Sampled in Both Campaigns")
    if overlap.is_empty or overlap_samples.empty:
        st.info("The matched fields don't overlap, so there is no shared area to compare.")
    else:
        change_table = change_summary(overlap_samples, base, latest, names, labels)
        st.dataframe(change_table, hide_index=True)

# Executive summary
st.subheader("Executive Summary Stats")
st.markdown(executive_summary(carbon_stats(matched_samples), change_table, names, labels,
                              campaign_ids, org_name))






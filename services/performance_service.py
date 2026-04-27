from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import pandas as pd


MILESTONE_LEVELS = [50, 100, 250, 500, 1000]


@dataclass
class ExplanationPackage:
    branch_name: str
    sol: str
    report_date: pd.Timestamp
    previous_date: pd.Timestamp | None
    metric_rows: List[Dict]
    key_points: List[str]
    exception_rows: List[Dict]


class PerformanceService:
    """Analytics helpers for branch, region, milestone, and document intelligence."""

    @staticmethod
    def facts_to_wide(facts: pd.DataFrame) -> pd.DataFrame:
        if facts.empty:
            return pd.DataFrame()
        wide = (
            facts.pivot_table(index=["sol", "date"], columns="metric", values="value", aggfunc="sum")
            .reset_index()
            .copy()
        )
        wide.columns.name = None
        wide["sol"] = wide["sol"].astype(str).str.zfill(4)
        wide["date"] = pd.to_datetime(wide["date"])
        return wide

    @staticmethod
    def latest_snapshot(facts: pd.DataFrame, branches: pd.DataFrame) -> pd.DataFrame:
        wide = PerformanceService.facts_to_wide(facts)
        if wide.empty:
            return wide
        latest_date = wide["date"].max()
        snap = wide[wide["date"] == latest_date].copy()
        if not branches.empty:
            merged = snap.merge(
                branches[["code", "nameEn", "district", "populationGroup", "size", "openDate"]],
                left_on="sol",
                right_on="code",
                how="left",
            )
        else:
            merged = snap
        return merged

    @staticmethod
    def add_growth_columns(wide: pd.DataFrame, metric_names: List[str]) -> pd.DataFrame:
        if wide.empty:
            return wide
        frame = wide.sort_values(["sol", "date"]).copy()
        for metric in metric_names:
            if metric not in frame.columns:
                frame[metric] = 0.0
            prev_col = f"{metric}_prev"
            delta_col = f"{metric}_delta"
            frame[prev_col] = frame.groupby("sol")[metric].shift(1).fillna(0.0)
            frame[delta_col] = frame[metric] - frame[prev_col]
        return frame

    @staticmethod
    def compute_branch_scores(snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot.empty:
            return snapshot
        frame = snapshot.copy()
        for metric in ["Bus", "Dep", "Adv", "CASA_PCT", "CD_Ratio", "Branch_PL", "NPA"]:
            if metric not in frame.columns:
                frame[metric] = 0.0

        frame["performance_score"] = (
            frame["Bus"].rank(pct=True).fillna(0) * 35
            + frame["Dep"].rank(pct=True).fillna(0) * 15
            + frame["Adv"].rank(pct=True).fillna(0) * 15
            + frame["CASA_PCT"].rank(pct=True).fillna(0) * 15
            + frame["Branch_PL"].rank(pct=True).fillna(0) * 10
            + (1 - frame["NPA"].rank(pct=True).fillna(0)) * 5
            + (1 - frame["CD_Ratio"].rank(pct=True).fillna(0)) * 5
        ).round(1)

        def classify(score: float) -> str:
            if score >= 75:
                return "Leading"
            if score >= 55:
                return "Stable"
            return "Needs Focus"

        frame["performance_band"] = frame["performance_score"].apply(classify)
        return frame.sort_values("performance_score", ascending=False)

    @staticmethod
    def milestone_hits(snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot.empty:
            return pd.DataFrame()
        rows = []
        for _, row in snapshot.iterrows():
            for metric in ["Bus", "Dep", "Adv"]:
                value_cr = float(row.get(metric, 0) or 0) / 100
                for level in MILESTONE_LEVELS:
                    if value_cr >= level:
                        rows.append(
                            {
                                "sol": row.get("sol"),
                                "branch_name": row.get("nameEn", row.get("sol")),
                                "metric": metric,
                                "milestone": f"{level} Cr",
                                "current_value_cr": round(value_cr, 2),
                                "district": row.get("district", ""),
                            }
                        )
        if not rows:
            return pd.DataFrame()
        hits = pd.DataFrame(rows).drop_duplicates(subset=["sol", "metric", "milestone"])
        return hits.sort_values(["metric", "current_value_cr"], ascending=[True, False])

    @staticmethod
    def upcoming_anniversaries(branches: pd.DataFrame, reference_date: datetime | None = None, within_days: int = 45) -> pd.DataFrame:
        if branches.empty or "openDate" not in branches.columns:
            return pd.DataFrame()
        ref = pd.Timestamp(reference_date or datetime.now()).normalize()
        frame = branches.copy()
        frame["openDate"] = pd.to_datetime(frame["openDate"], errors="coerce")
        frame = frame.dropna(subset=["openDate"])
        frame["anniversary_this_year"] = frame["openDate"].apply(lambda d: pd.Timestamp(year=ref.year, month=d.month, day=d.day))
        frame["anniversary_date"] = frame["anniversary_this_year"].where(
            frame["anniversary_this_year"] >= ref,
            frame["anniversary_this_year"] + pd.DateOffset(years=1),
        )
        frame["days_to_anniversary"] = (frame["anniversary_date"] - ref).dt.days
        frame["years_completed"] = frame["anniversary_date"].dt.year - frame["openDate"].dt.year
        frame = frame[(frame["days_to_anniversary"] >= 0) & (frame["days_to_anniversary"] <= within_days)]
        return frame.sort_values("days_to_anniversary")[
            ["code", "nameEn", "district", "anniversary_date", "days_to_anniversary", "years_completed"]
        ]

    @staticmethod
    def marketing_focus_report(snapshot: pd.DataFrame, targets: pd.DataFrame | None = None) -> pd.DataFrame:
        if snapshot.empty:
            return pd.DataFrame()
        frame = snapshot.copy()
        for metric in ["Bus", "Dep", "Adv", "CASA_PCT", "CD_Ratio", "Branch_PL"]:
            if metric not in frame.columns:
                frame[metric] = 0.0
        frame["focus_reason"] = ""
        frame.loc[frame["CASA_PCT"] < 35, "focus_reason"] += "Low CASA mix; "
        frame.loc[frame["CD_Ratio"] > 75, "focus_reason"] += "High CD ratio; "
        frame.loc[frame["Branch_PL"] < 0, "focus_reason"] += "Negative P&L; "
        if targets is not None and not targets.empty:
            target_map = targets.set_index("metric")["target_value"].to_dict()
            bus_target = float(target_map.get("Bus", 0) or 0)
            if bus_target > 0:
                frame["bus_achievement_pct"] = (frame["Bus"] / bus_target * 100).round(2)
                frame.loc[frame["bus_achievement_pct"] < 70, "focus_reason"] += "Below 70% of business target; "
        frame["focus_reason"] = frame["focus_reason"].str.strip().str.rstrip(";")
        focused = frame[frame["focus_reason"] != ""].copy()
        if focused.empty:
            return pd.DataFrame()
        return focused[
            ["sol", "nameEn", "district", "Bus", "Dep", "Adv", "CASA_PCT", "CD_Ratio", "Branch_PL", "focus_reason"]
        ].sort_values(["district", "nameEn"])

    @staticmethod
    def build_explanation_package(
        facts: pd.DataFrame,
        branches: pd.DataFrame,
        exceptions: pd.DataFrame,
        sol: str,
        report_date: pd.Timestamp,
    ) -> ExplanationPackage | None:
        if facts.empty:
            return None
        sol = str(sol).zfill(4)
        facts = facts.copy()
        facts["date"] = pd.to_datetime(facts["date"])
        branch_facts = facts[facts["sol"] == sol].sort_values("date")
        current = branch_facts[branch_facts["date"] == pd.to_datetime(report_date)]
        if current.empty:
            return None
        previous_dates = sorted(branch_facts[branch_facts["date"] < pd.to_datetime(report_date)]["date"].unique())
        prev_date = previous_dates[-1] if previous_dates else None
        prev = branch_facts[branch_facts["date"] == prev_date] if prev_date is not None else pd.DataFrame()

        current_map = current.groupby("metric")["value"].sum().to_dict()
        prev_map = prev.groupby("metric")["value"].sum().to_dict() if not prev.empty else {}
        metric_rows = []
        for metric in ["Bus", "Dep", "Adv", "CASA_PCT", "CD_Ratio", "Branch_PL", "NPA", "CASH_TOTAL", "CASH_CRL"]:
            cur_val = float(current_map.get(metric, 0) or 0)
            prev_val = float(prev_map.get(metric, 0) or 0)
            metric_rows.append(
                {
                    "metric": metric,
                    "current_value": cur_val,
                    "previous_value": prev_val,
                    "movement": cur_val - prev_val,
                }
            )

        branch_name = sol
        if not branches.empty:
            match = branches[branches["code"].astype(str).str.zfill(4) == sol]
            if not match.empty:
                branch_name = match.iloc[0].get("nameEn", sol)

        key_points = []
        bus_move = next((r["movement"] for r in metric_rows if r["metric"] == "Bus"), 0)
        dep_move = next((r["movement"] for r in metric_rows if r["metric"] == "Dep"), 0)
        casa_mix = next((r["current_value"] for r in metric_rows if r["metric"] == "CASA_PCT"), 0)
        cd_ratio = next((r["current_value"] for r in metric_rows if r["metric"] == "CD_Ratio"), 0)
        pl_value = next((r["current_value"] for r in metric_rows if r["metric"] == "Branch_PL"), 0)
        cash_total = next((r["current_value"] for r in metric_rows if r["metric"] == "CASH_TOTAL"), 0)
        cash_crl = next((r["current_value"] for r in metric_rows if r["metric"] == "CASH_CRL"), 0)

        key_points.append(f"Total business moved by {bus_move / 100:,.2f} Cr versus the previous available date.")
        key_points.append(f"Deposit movement for the period is {dep_move / 100:,.2f} Cr with CASA mix at {casa_mix:,.2f}%.")
        if cd_ratio > 75:
            key_points.append(f"CD ratio stands elevated at {cd_ratio:,.2f}% and needs active balance-sheet correction.")
        if pl_value < 0:
            key_points.append(f"The branch is currently in a loss position of {abs(pl_value):,.2f} lakh.")
        if cash_total > cash_crl > 0:
            key_points.append(f"Cash holding exceeds CRL by {cash_total - cash_crl:,.2f} lakh and must be explained.")

        exc_rows = []
        if not exceptions.empty:
            exc = exceptions.copy()
            exc["date"] = pd.to_datetime(exc["date"])
            exc = exc[(exc["sol"].astype(str).str.zfill(4) == sol) & (exc["date"] == pd.to_datetime(report_date))]
            exc_rows = exc.to_dict("records")

        return ExplanationPackage(
            branch_name=branch_name,
            sol=sol,
            report_date=pd.to_datetime(report_date),
            previous_date=pd.to_datetime(prev_date) if prev_date is not None else None,
            metric_rows=metric_rows,
            key_points=key_points,
            exception_rows=exc_rows,
        )

"""One-off script to fix a malformed report where the full JSON was stored in executive_summary."""

import asyncio
import json
from sqlalchemy import select
from app.models.database import async_session_factory, Report


async def fix_report():
    async with async_session_factory() as session:
        result = await session.execute(select(Report))
        reports = result.scalars().all()

        for report in reports:
            summary = report.executive_summary or ""
            if not summary.strip().startswith("{"):
                continue

            print(f"Fixing report {report.id}...")
            try:
                # Try to parse the stored JSON blob
                start = summary.index("{")
                end = summary.rindex("}") + 1
                data = json.loads(summary[start:end])

                report.executive_summary = data.get("executive_summary", summary)
                report.detailed_findings = data.get("detailed_findings", {})
                report.themes = data.get("themes", [])
                report.recommendations = data.get("recommendations", [])
                report.report_metadata = data.get("metadata", {})

                await session.commit()
                print(f"Fixed report {report.id} successfully.")
            except (ValueError, json.JSONDecodeError) as e:
                print(f"Could not parse report {report.id}: {e}")


asyncio.run(fix_report())

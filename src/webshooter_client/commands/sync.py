"""CLI presentation for the sync command."""

from datetime import date
from typing import Optional

from webshooter_client.common.output_utils import print_table
from webshooter_client.sync import get_local_store_status, reindex_local_store, sync_competitions


def sync(
    card: Optional[str] = None,
    since: Optional[str] = None,
    full: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> None:
    """Download competitions missing from the local store and print a summary."""
    since_date = date.fromisoformat(since) if since else None

    report = sync_competitions(
        card=card,
        since=since_date,
        full=full,
        dry_run=dry_run,
        limit=limit,
    )

    print(f"Local store: {report.cache_dir}")
    if report.watermark:
        print(f"Latest downloaded competition: {report.watermark.isoformat()}")
    else:
        print("Latest downloaded competition: none (store is empty)")

    if report.up_to_date:
        print("\nAlready up to date - nothing new to download.")
        return

    if report.dry_run:
        print(f"\nWould download {len(report.considered)} competition(s):\n")
        print_table(
            [[c.id, c.competition_date.isoformat(), c.type.display_name, c.name] for c in report.considered],
            headers=["ID", "Date", "Type", "Competition"],
        )
        return

    print(f"\nDownloaded {len(report.downloaded)} of {len(report.considered)} competition(s).")

    if report.with_my_results:
        print(f"\nNew results for card {report.card}:\n")
        print_table(
            [
                [c.id, c.competition_date.isoformat(), c.type, ", ".join(c.my_weapon_classes), c.name]
                for c in report.with_my_results
            ],
            headers=["ID", "Date", "Type", "Class", "Competition"],
        )
    elif report.card:
        print(f"\nNo new results for card {report.card}.")

    if report.failed:
        print(f"\nSkipped {len(report.failed)} competition(s) (results not available):\n")
        print_table(
            [[f["id"], f["name"], f["error"][:60]] for f in report.failed],
            headers=["ID", "Competition", "Reason"],
        )


def reindex(card: Optional[str] = None) -> None:
    """Rebuild the index from already-downloaded data and print a summary."""
    report = reindex_local_store(card=card)

    print(f"Local store: {report.cache_dir}")
    print(f"Indexed {len(report.downloaded)} of {len(report.considered)} downloaded competition(s).")
    if report.card:
        print(f"Competitions with results for card {report.card}: {len(report.with_my_results)}")
    if report.failed:
        print(f"Unreadable: {len(report.failed)}")


def status(card: Optional[str] = None) -> None:
    """Print what the local store contains, without any network access."""
    store = get_local_store_status(card=card)

    print(f"Local store:        {store.cache_dir}")
    print(f"Competitions:       {store.competition_count}")
    print(f"Date range:         {store.earliest_date or '-'} .. {store.latest_date or '-'}")
    print(f"Last sync:          {store.last_sync or 'never'}")
    print(f"Card:               {store.card or '-'}")
    print(f"With your results:  {store.my_competition_count}")

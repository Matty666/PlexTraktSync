import click

from plextraktsync.commands.login import ensure_login
from plextraktsync.factory import factory


def unmatched(no_progress_bar: bool, local: bool):
    factory.run_config.update(progressbar=not no_progress_bar)
    ensure_login()
    plex = factory.plex_api
    mf = factory.media_factory
    wc = factory.walk_config
    walker = factory.walker

    if not wc.is_valid():
        click.echo("Nothing to scan, this is likely due conflicting options given.")
        return

    failed = []
    if local:
        for pm in walker.get_plex_movies():
            if pm.guids[0].provider == "local":
                failed.append(pm)
    else:
        for pm in walker.get_plex_movies():
            movie = mf.resolve_any(pm)
            if not movie:
                failed.append(pm)

    for i, pm in enumerate(failed):
        p = pm.item
        url = plex.media_url(pm)
        print("=", i, "=" * 80)
        print(f"No match: {pm}")
        print(f"URL: {url}")
        print(f"Title: {p.title}")
        print(f"Year: {p.year}")
        print(f"Updated At: {p.updatedAt}")
        for location in p.locations:
            print(f"Location: {location}")

        print("")

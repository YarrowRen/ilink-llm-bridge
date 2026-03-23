#!/usr/bin/env python3
"""iLink ↔ LLM Bridge — entry point."""
import asyncio
import sys

from .config.loader import load_config
from .history.manager import HistoryManager
from .ilink.api import ILinkClient
from .llm.registry import create_provider
from .bridge.handler import MessageHandler
from .bridge.loop import run_loop
from .util.logger import logger, set_log_level


def main() -> None:
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Config error: {e}", file=sys.stderr)
        sys.exit(1)

    set_log_level(cfg.log.level)
    logger.info(f"Starting iLink-LLM Bridge (provider={cfg.provider.name})")

    provider = create_provider(cfg.provider)
    client = ILinkClient(
        base_url=cfg.ilink.base_url,
        token=cfg.ilink.token,
        cdn_base_url=cfg.ilink.cdn_base_url,
        route_tag=cfg.ilink.route_tag,
    )
    history = HistoryManager(
        history_dir=cfg.storage.history_dir,
        max_length=cfg.bot.max_history_length,
    )
    handler = MessageHandler(
        client=client,
        provider=provider,
        provider_cfg=cfg.provider,
        bot_cfg=cfg.bot,
        history=history,
        media_dir=cfg.storage.media_dir,
    )

    try:
        asyncio.run(run_loop(cfg, handler))
    except KeyboardInterrupt:
        logger.info("Bridge stopped.")


if __name__ == "__main__":
    main()

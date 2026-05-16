"""Fullwidth / CJK punctuation fragments reused by deterministic zh copy (not natural-language sentences)."""

from __future__ import annotations

from typing import Final, Tuple

ZH_IDEOGRAPHIC_COMMA: Final[str] = "、"
ZH_FULLWIDTH_SEMICOLON: Final[str] = "；"
ZH_FULLWIDTH_QUESTION_MARK: Final[str] = "？"
ZH_FULLWIDTH_EXCLAMATION: Final[str] = "！"
ZH_FULLWIDTH_COMMA: Final[str] = "，"
ZH_FULLWIDTH_PERIOD: Final[str] = "。"
ZH_FULLWIDTH_COLON: Final[str] = "："
ZH_SENTENCE_TERMINATORS: Final[Tuple[str, str, str]] = (ZH_FULLWIDTH_PERIOD, ZH_FULLWIDTH_EXCLAMATION, ZH_FULLWIDTH_QUESTION_MARK)
# Natural-language joiner for zh enumerations ("A and B").
ZH_CONJUNCTION_AND: Final[str] = " 和 "

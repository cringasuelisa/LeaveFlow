"""Filtre custom pentru template-uri."""
import hashlib

from django import template

register = template.Library()


# Paleta de culori vesele dar bine contrastate cu textul alb
COLOR_PALETTE = [
    "#0d6efd",  # albastru
    "#198754",  # verde
    "#fd7e14",  # portocaliu
    "#6f42c1",  # mov
    "#d63384",  # roz
    "#20c997",  # turcoaz
    "#dc3545",  # rosu
    "#0dcaf0",  # cyan
    "#6610f2",  # indigo
    "#e83e8c",  # magenta
    "#28a745",  # verde-2
    "#17a2b8",  # info
    "#ff6b6b",  # coral
    "#5e60ce",  # violet
    "#ffa94d",  # piersica
]


def _hash_to_index(value: str, modulo: int) -> int:
    h = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % modulo


@register.filter
def user_color(user) -> str:
    """Culoare deterministica pentru un user, in functie de username."""
    if user is None:
        return COLOR_PALETTE[0]
    key = getattr(user, "username", None) or str(user)
    return COLOR_PALETTE[_hash_to_index(key, len(COLOR_PALETTE))]


@register.filter
def user_initials(user) -> str:
    """Maxim 2 caractere: initiale din nume/prenume sau primele 2 din username."""
    if user is None:
        return "?"
    first = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    if first or last:
        return ((first[:1] + last[:1]) or "?").upper()
    username = getattr(user, "username", "") or ""
    return (username[:2] or "?").upper()

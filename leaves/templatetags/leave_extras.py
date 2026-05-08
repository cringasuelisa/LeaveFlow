"""Filtre custom pentru template-uri (culori si initiale)."""
import hashlib

from django import template

register = template.Library()


COLOR_PALETTE = [
    "#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#d63384",
    "#20c997", "#dc3545", "#0dcaf0", "#6610f2", "#e83e8c",
    "#28a745", "#17a2b8", "#ff6b6b", "#5e60ce", "#ffa94d",
]


def _hash_to_index(value, modulo):
    h = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % modulo


@register.filter
def user_color(user):
    if user is None:
        return COLOR_PALETTE[0]
    key = getattr(user, "username", None) or str(user)
    return COLOR_PALETTE[_hash_to_index(key, len(COLOR_PALETTE))]


@register.filter
def user_initials(user):
    if user is None:
        return "?"
    first = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    if first or last:
        return ((first[:1] + last[:1]) or "?").upper()
    username = getattr(user, "username", "") or ""
    return (username[:2] or "?").upper()

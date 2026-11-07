"""Shared Sphinx metadata footer for component manuals."""

# -- Render page metadata visibly in HTML output -----------------------------
# Each page carries YAML frontmatter, which MyST stores in env.metadata. Older
# pages end with a <!-- PKB-metadata ... --> comment instead. Either way, this
# hook appends a styled info table, with tags as chips.

import html as _html
import json as _json
import re as _re
from pathlib import Path as _Path

_META_RE = _re.compile(
    r'<!--\s*PKB-metadata\s*\n(.*?)-->',
    _re.DOTALL,
)

_LEGACY_KEYS = {'last_updated': 'updated_time', 'commit': 'git_commit'}

_LABEL_MAP = {
    'updated_time': ('Last Updated', '最后更新'),
    'git_commit': ('Commit', '提交'),
    'updated_by': ('Updated By', '更新者'),
    'source': ('Source', '来源'),
    'owners': ('Owners', '归属与责任人'),
    'ttl': ('TTL', '有效期'),
    'review_status': ('Review Status', '审核状态'),
    'review_score': ('Review Score', '审核评分'),
    'reviewed_by': ('Reviewed By', '审核人'),
    'confidentiality': ('Confidentiality', '保密等级'),
    'tags': ('Tags', '标签'),
}

_TAG_KEYS = ('domain', 'technology', 'concepts', 'audience', 'status')

_STATUS_ZH = {'pending': '待审核', 'approved': '已审核'}

_LEVEL_LABELS = {
    'L1': ('L1 · Public', 'L1 · 公开'),
    'L2': ('L2 · Internal', 'L2 · 内部'),
    'L3': ('L3 · Confidential', 'L3 · 机密'),
    'L4': ('L4 · Secret', 'L4 · 秘密'),
    'L5': ('L5 · Top Secret', 'L5 · 绝密'),
}


def _page_metadata(app, docname):
    """Frontmatter from MyST, else the legacy footer, with frontmatter key names."""
    meta = {
        key: value
        for key, value in app.env.metadata.get(docname, {}).items()
        if key in _LABEL_MAP and (key in ('source', 'owners', 'ttl') or value not in (None, '', 'null'))
    }
    if meta:
        return meta
    source_path = _Path(app.srcdir) / f'{docname}.md'
    if not source_path.exists():
        return {}
    m = _META_RE.search(source_path.read_text(encoding='utf-8'))
    if not m:
        return {}
    for line in m.group(1).strip().splitlines():
        key, sep, val = line.strip().partition(':')
        if sep and val.strip():
            meta[_LEGACY_KEYS.get(key.strip(), key.strip())] = val.strip()
    return meta


def _knowledge_metadata_text(key, raw, is_zh=False):
    """Format MyST JSON metadata as text; HTML escaping belongs to the renderer."""
    import json

    value = raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            pass
    unknown = 'unknown'
    if key == 'source':
        if isinstance(value, list):
            return '; '.join(str(v) for v in value) if value else unknown
        return str(value) if value not in (None, '') else unknown
    if key == 'owners':
        if value is None or value == '':
            value = {}
        if not isinstance(value, dict):
            return 'owners 格式无效' if is_zh else 'Invalid owners metadata'
        roles = (('created_by', '创建者' if is_zh else 'Created by'),
                 ('updated_by', '最近更新者' if is_zh else 'Updated by'),
                 ('responsible', '负责人' if is_zh else 'Responsible'))
        parts = []
        for role, label in roles:
            people = value.get(role)
            if isinstance(people, list):
                people = ', '.join(str(p) for p in people)
            parts.append(f'{label}: {people or unknown}')
        return '; '.join(parts)
    return str(value) if value not in (None, '') else 'unknown'


def _tags_html(raw):
    # MyST stores a nested frontmatter mapping as a JSON string.
    try:
        tags = _json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return ''
    if not isinstance(tags, dict):
        return ''
    chips = []
    for key in _TAG_KEYS:
        values = tags.get(key) or []
        for value in [values] if isinstance(values, str) else values:
            chips.append(
                f'<span class="pkb-tag pkb-tag-{key}" title="{key}">{_html.escape(str(value))}</span>'
            )
    return ''.join(chips)


_SOURCE_URL_RE = _re.compile(r'^(https?://\S+)')


def _source_entries(raw):
    """Normalize the ``source`` frontmatter value (list or JSON string) into a list of strings."""
    value = raw
    if isinstance(raw, str):
        try:
            value = _json.loads(raw)
        except (ValueError, TypeError):
            value = [raw]
    if value is None:
        value = []
    if not isinstance(value, list):
        value = [str(value)]
    return [str(v).strip() for v in value if str(v).strip()]


def _source_parts(entry):
    """Split one source entry into ('link', url, label) or ('text', text).

    ``https://www.lua.org/... (Lua 5.1 reference manual)`` becomes
    ('link', 'https://www.lua.org/...', 'Lua 5.1 reference manual').
    Local paths (e.g. ``doc/03-tech-stack.md``) stay plain text.
    """
    m = _SOURCE_URL_RE.match(entry)
    if not m:
        return ('text', entry)
    url = m.group(1).rstrip('.,;')
    rest = entry[m.end():]
    dm = _re.search(r'\(([^()]*)\)\s*$', rest)
    label = (dm.group(1).strip() if dm else '') or url
    return ('link', url, label)


def _inject_pkb_metadata(app, doctree, docname):
    """Append a compact one- or two-line metadata footer (no table)."""
    from docutils import nodes

    meta = _page_metadata(app, docname)
    if not meta:
        return

    is_zh = app.config.language != 'en'
    unknown = 'unknown'

    owners_labels = (
        ('创建者', '最近更新者', '负责人') if is_zh else ('Created by', 'Updated by', 'Responsible')
    )
    segs = [f"{label}: Walter Fan" for label in owners_labels]

    if meta.get('updated_time'):
        segs.append(f"{'最后更新' if is_zh else 'Last Updated'}: {meta['updated_time']}")
    if meta.get('git_commit'):
        segs.append(f"{'提交' if is_zh else 'Commit'}: {meta['git_commit']}")
    if meta.get('confidentiality'):
        level = str(meta['confidentiality']).strip().upper()
        if level not in _LEVEL_LABELS:
            level = 'L1'
        segs.append(
            f"{'保密等级' if is_zh else 'Confidentiality'}: {_LEVEL_LABELS[level][1 if is_zh else 0]}"
        )
    ttl = meta.get('ttl')
    if ttl not in (None, '', 'null'):
        segs.append(f"{'有效期' if is_zh else 'TTL'}: {ttl}")

    container = nodes.container(classes=['pkb-metadata-footer', 'pkb-metadata-compact'])
    container += nodes.paragraph(text=' · '.join(segs))

    raw_source = meta.get('source')
    if raw_source:
        parts = [_source_parts(e) for e in _source_entries(raw_source)]
        if any(part[1] for part in parts):
            para = nodes.paragraph()
            para += nodes.strong(text=('来源' if is_zh else 'Source') + ': ')
            for i, part in enumerate(parts):
                if i:
                    para += nodes.Text('; ')
                if part[0] == 'link':
                    ref = nodes.reference(refuri=part[1])
                    ref += nodes.Text(part[2])
                    para += ref
                else:
                    para += nodes.Text(part[1])
            container += para

    doctree += container

"""Notion content parser for extracting and formatting text."""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class NotionParser:
    """Parser for Notion content blocks and pages."""
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract plain text from Notion blocks.
        
        Args:
            blocks: List of Notion block objects
            
        Returns:
            Concatenated plain text content
        """
        text_parts = []
        
        for block in blocks:
            text = self._extract_text_from_block(block)
            if text:
                text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _extract_text_from_block(self, block: Dict[str, Any]) -> Optional[str]:
        """Extract text from a single Notion block.
        
        Args:
            block: Single Notion block object
            
        Returns:
            Extracted text or None if no text content
        """
        block_type = block.get("type", "")
        
        # Handle different block types
        if block_type == "paragraph":
            return self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
        
        elif block_type == "heading_1":
            return f"# {self._extract_rich_text(block.get('heading_1', {}).get('rich_text', []))}"
        
        elif block_type == "heading_2":
            return f"## {self._extract_rich_text(block.get('heading_2', {}).get('rich_text', []))}"
        
        elif block_type == "heading_3":
            return f"### {self._extract_rich_text(block.get('heading_3', {}).get('rich_text', []))}"
        
        elif block_type == "bulleted_list_item":
            return f"• {self._extract_rich_text(block.get('bulleted_list_item', {}).get('rich_text', []))}"
        
        elif block_type == "numbered_list_item":
            return f"1. {self._extract_rich_text(block.get('numbered_list_item', {}).get('rich_text', []))}"
        
        elif block_type == "to_do":
            todo_data = block.get("to_do", {})
            checked = todo_data.get("checked", False)
            text = self._extract_rich_text(todo_data.get("rich_text", []))
            checkbox = "[x]" if checked else "[ ]"
            return f"{checkbox} {text}"
        
        elif block_type == "code":
            code_data = block.get("code", {})
            language = code_data.get("language", "")
            text = self._extract_rich_text(code_data.get("rich_text", []))
            return f"```{language}\n{text}\n```"
        
        elif block_type == "quote":
            return f"> {self._extract_rich_text(block.get('quote', {}).get('rich_text', []))}"
        
        elif block_type == "callout":
            callout_data = block.get("callout", {})
            icon = callout_data.get("icon", {}).get("emoji", "💡")
            text = self._extract_rich_text(callout_data.get("rich_text", []))
            return f"{icon} {text}"
        
        elif block_type == "divider":
            return "---"
        
        elif block_type == "table":
            return self._extract_table_text(block.get("table", {}))
        
        # Handle child blocks recursively
        if "children" in block:
            child_text = self.extract_text_from_blocks(block["children"])
            if child_text:
                return child_text
        
        return None
    
    def _extract_rich_text(self, rich_text: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array.
        
        Args:
            rich_text: List of rich text objects
            
        Returns:
            Concatenated plain text
        """
        if not rich_text:
            return ""
        
        text_parts = []
        for text_obj in rich_text:
            if "plain_text" in text_obj:
                text_parts.append(text_obj["plain_text"])
        
        return "".join(text_parts)
    
    def _extract_table_text(self, table_data: Dict[str, Any]) -> str:
        """Extract text from table data.
        
        Args:
            table_data: Table block data
            
        Returns:
            Formatted table text
        """
        # Table blocks themselves do not include row contents; rows usually
        # arrive as adjacent "table_row" blocks (or in block["children"] if
        # fetched with children). Callers that want richer tables should use
        # the higher-level helpers added below which stitch rows together.
        width = table_data.get("table_width")
        return f"[Table with {width if width is not None else '?'} columns]"
    
    def parse_page_properties(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse page properties.
        
        Args:
            page: Notion page object
            
        Returns:
            Dictionary of parsed properties
        """
        properties = {}
        page_properties = page.get("properties", {})
        
        for prop_name, prop_data in page_properties.items():
            prop_type = prop_data.get("type", "")
            
            if prop_type == "title":
                properties[prop_name] = self._extract_rich_text(prop_data.get("title", []))
            
            elif prop_type == "rich_text":
                properties[prop_name] = self._extract_rich_text(prop_data.get("rich_text", []))
            
            elif prop_type == "select":
                select_data = prop_data.get("select", {})
                properties[prop_name] = select_data.get("name") if select_data else None
            
            elif prop_type == "multi_select":
                multi_select_data = prop_data.get("multi_select", [])
                properties[prop_name] = [item.get("name") for item in multi_select_data]
            
            elif prop_type == "date":
                date_data = prop_data.get("date", {})
                properties[prop_name] = date_data.get("start") if date_data else None
            
            elif prop_type == "checkbox":
                properties[prop_name] = prop_data.get("checkbox", False)
            
            elif prop_type == "number":
                properties[prop_name] = prop_data.get("number")
            
            elif prop_type == "url":
                properties[prop_name] = prop_data.get("url")
            
            elif prop_type == "email":
                properties[prop_name] = prop_data.get("email")
            
            elif prop_type == "phone_number":
                properties[prop_name] = prop_data.get("phone_number")
            
            else:
                # For unknown property types, store the raw data
                properties[prop_name] = prop_data
        
        return properties

    def flatten_blocks_to_text(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert a recursive block tree into a readable plain-text string.
        
        This function walks the list of Notion blocks (which may be a flat list
        or include nested "children") and produces a text optimized for LLMs.
        
        Output formatting rules (subset of Markdown):
        - Headings: "# ", "## ", "### "
        - Paragraphs: plain lines
        - Bulleted lists: lines prefixed with "• "
        - Numbered lists: lines prefixed with incrementing "1. ", "2. ", ...
        - To-do items: "[x] " or "[ ] "
        - Quotes: lines prefixed with "> "
        - Code blocks: fenced with triple backticks and language if present
        - Dividers: "---"
        - Tables: rendered as Markdown-like pipe-delimited rows if row blocks
          are available, otherwise a compact descriptor
        
        Example:
            text = parser.flatten_blocks_to_text(blocks)
            # => "# Title\nParagraph...\n• Item 1\n• Item 2\n---\n| Col A | Col B |\n|---|---|\n| v1 | v2 |"
        """
        lines: List[str] = []

        i = 0
        n = len(blocks)

        def rich(block: Dict[str, Any], key: str) -> str:
            return self._extract_rich_text(block.get(key, {}).get("rich_text", []))

        while i < n:
            block = blocks[i]
            btype = block.get("type", "")

            if btype in ("heading_1", "heading_2", "heading_3"):
                level = {"heading_1": 1, "heading_2": 2, "heading_3": 3}[btype]
                text = rich(block, btype)
                if text:
                    lines.append(f"{'#' * level} {text}")
                i += 1
                continue

            if btype == "paragraph":
                text = rich(block, "paragraph")
                if text:
                    lines.append(text)
                i += 1
                continue

            if btype in ("bulleted_list_item", "numbered_list_item"):
                # Group contiguous list items of the same kind
                items: List[str] = []
                start = i
                while i < n and blocks[i].get("type") == btype:
                    items.append(self._extract_rich_text(blocks[i][btype].get("rich_text", [])))
                    i += 1
                if btype == "bulleted_list_item":
                    for t in items:
                        if t:
                            lines.append(f"• {t}")
                else:
                    for idx, t in enumerate(items, start=1):
                        if t:
                            lines.append(f"{idx}. {t}")
                continue

            if btype == "to_do":
                todo = block.get("to_do", {})
                checked = todo.get("checked", False)
                text = self._extract_rich_text(todo.get("rich_text", []))
                checkbox = "[x]" if checked else "[ ]"
                lines.append(f"{checkbox} {text}")
                i += 1
                continue

            if btype == "quote":
                text = rich(block, "quote")
                if text:
                    lines.append(f"> {text}")
                i += 1
                continue

            if btype == "code":
                code = block.get("code", {})
                language = code.get("language", "")
                text = self._extract_rich_text(code.get("rich_text", []))
                lines.append(f"```{language}\n{text}\n```")
                i += 1
                continue

            if btype == "divider":
                lines.append("---")
                i += 1
                continue

            if btype == "table":
                # Build a simple Markdown-like table by consuming following
                # contiguous table_row blocks. If no rows are available,
                # fall back to a compact descriptor.
                table = block.get("table", {})
                rows: List[List[str]] = []

                j = i + 1
                while j < n and blocks[j].get("type") == "table_row":
                    cells = blocks[j].get("table_row", {}).get("cells", [])
                    row_texts: List[str] = []
                    for cell in cells:
                        # cell is a list of rich_text objects
                        row_texts.append(self._extract_rich_text(cell))
                    rows.append(row_texts)
                    j += 1

                if rows:
                    # Render header separator after the first row
                    header = rows[0]
                    lines.append("| " + " | ".join(header) + " |")
                    lines.append("|" + "|".join(["---" for _ in header]) + "|")
                    for r in rows[1:]:
                        lines.append("| " + " | ".join(r) + " |")
                    i = j
                    continue
                else:
                    lines.append(self._extract_table_text(table))
                    i += 1
                    continue

            if btype == "table_row":
                # If we see an isolated row (without a preceding table), render as CSV line
                cells = block.get("table_row", {}).get("cells", [])
                row_texts = [self._extract_rich_text(cell) for cell in cells]
                lines.append(", ".join(row_texts))
                i += 1
                continue

            # If nested children were provided, render them recursively
            if "children" in block and isinstance(block["children"], list):
                child_text = self.flatten_blocks_to_text(block["children"])
                if child_text:
                    lines.append(child_text)
                i += 1
                continue

            # Fallback to existing single-block extractor
            fallback = self._extract_text_from_block(block)
            if fallback:
                lines.append(fallback)
            i += 1

        text = "\n".join(lines)
        return self.sanitize_text(text)

    def blocks_to_elements(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert blocks into a lightweight JSON array for LLM analysis.
        
        Returns a list of dictionaries. Each dictionary has a mandatory
        "type" field and additional fields depending on type:
        - heading: {"type":"heading","level":1|2|3,"text":str}
        - paragraph: {"type":"paragraph","text":str}
        - bulleted_list: {"type":"bulleted_list","items":[str]}
        - numbered_list: {"type":"numbered_list","items":[str]}
        - todo_list: {"type":"todo_list","items":[{"checked":bool,"text":str}]}
        - quote: {"type":"quote","text":str}
        - code: {"type":"code","language":str,"code":str}
        - divider: {"type":"divider"}
        - table: {"type":"table","rows":[[str,...], ...]}
        
        Example:
            elements = parser.blocks_to_elements(blocks)
            # => [
            #   {"type":"heading","level":1,"text":"Title"},
            #   {"type":"paragraph","text":"Intro paragraph"},
            #   {"type":"bulleted_list","items":["Item 1","Item 2"]}
            # ]
        """
        elements: List[Dict[str, Any]] = []

        i = 0
        n = len(blocks)

        def rich(block: Dict[str, Any], key: str) -> str:
            return self._extract_rich_text(block.get(key, {}).get("rich_text", []))

        while i < n:
            block = blocks[i]
            btype = block.get("type", "")

            if btype in ("heading_1", "heading_2", "heading_3"):
                level = {"heading_1": 1, "heading_2": 2, "heading_3": 3}[btype]
                text = rich(block, btype)
                if text:
                    elements.append({"type": "heading", "level": level, "text": text})
                i += 1
                continue

            if btype == "paragraph":
                text = rich(block, "paragraph")
                if text:
                    elements.append({"type": "paragraph", "text": text})
                i += 1
                continue

            if btype in ("bulleted_list_item", "numbered_list_item"):
                items: List[str] = []
                kind = "bulleted_list" if btype == "bulleted_list_item" else "numbered_list"
                while i < n and blocks[i].get("type") == btype:
                    items.append(self._extract_rich_text(blocks[i][btype].get("rich_text", [])))
                    i += 1
                items = [t for t in items if t]
                if items:
                    elements.append({"type": kind, "items": items})
                continue

            if btype == "to_do":
                todos: List[Dict[str, Any]] = []
                while i < n and blocks[i].get("type") == "to_do":
                    todo = blocks[i].get("to_do", {})
                    todos.append({
                        "checked": bool(todo.get("checked", False)),
                        "text": self._extract_rich_text(todo.get("rich_text", []))
                    })
                    i += 1
                if todos:
                    elements.append({"type": "todo_list", "items": todos})
                continue

            if btype == "quote":
                text = rich(block, "quote")
                if text:
                    elements.append({"type": "quote", "text": text})
                i += 1
                continue

            if btype == "code":
                code = block.get("code", {})
                language = code.get("language", "")
                text = self._extract_rich_text(code.get("rich_text", []))
                elements.append({"type": "code", "language": language, "code": text})
                i += 1
                continue

            if btype == "divider":
                elements.append({"type": "divider"})
                i += 1
                continue

            if btype == "table":
                rows: List[List[str]] = []
                j = i + 1
                while j < n and blocks[j].get("type") == "table_row":
                    cells = blocks[j].get("table_row", {}).get("cells", [])
                    rows.append([self._extract_rich_text(cell) for cell in cells])
                    j += 1
                if rows:
                    elements.append({"type": "table", "rows": rows})
                    i = j
                    continue
                else:
                    elements.append({"type": "table", "rows": []})
                    i += 1
                    continue

            if btype == "table_row":
                # Standalone row: represent as single-row table
                cells = block.get("table_row", {}).get("cells", [])
                row = [self._extract_rich_text(cell) for cell in cells]
                elements.append({"type": "table", "rows": [row]})
                i += 1
                continue

            # Children (nested) handling: convert recursively and extend
            if "children" in block and isinstance(block["children"], list):
                child_elements = self.blocks_to_elements(block["children"])
                elements.extend(child_elements)
                i += 1
                continue

            # Fallback: use text extractor as paragraph if anything was found
            fallback = self._extract_text_from_block(block)
            if fallback:
                elements.append({"type": "paragraph", "text": fallback})
            i += 1

        return elements

    def sanitize_text(self, text: str) -> str:
        """Normalize text for LLM consumption.
        
        - Replace non-breaking spaces and odd unicode spaces with regular spaces
        - Normalize Windows/Mac line endings to \n
        - Trim trailing spaces on each line
        - Collapse 3+ blank lines into at most 2
        """
        if not text:
            return ""
        # Replace NBSP and similar
        cleaned = (
            text
            .replace("\u00a0", " ")  # non-breaking space
            .replace("\u2009", " ")  # thin space
            .replace("\u2002", " ")  # en space
            .replace("\u2003", " ")  # em space
        )
        # Normalize line endings
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        # Trim trailing spaces per line
        cleaned = "\n".join(line.rstrip() for line in cleaned.split("\n"))
        # Collapse excessive blank lines
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        return cleaned

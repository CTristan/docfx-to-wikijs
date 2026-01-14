"""Tests for the docfx_yml_to_wikijs module."""

import sys
from pathlib import Path
from unittest.mock import patch

from docfx_yml_to_wikijs import (
    ItemInfo,
    LinkTarget,
    as_text,
    build_link_targets,
    dot_safe,
    header_slug,
    is_member_kind,
    is_namespace_kind,
    is_type_kind,
    iter_main_items,
    load_managed_reference,
    main,
    md_codeblock,
    md_table,
    namespace_of,
    page_path_for_fullname,
    render_namespace_page,
    render_type_page,
    rewrite_xrefs,
    strip_yaml_mime_header,
)


def test_strip_yaml_mime_header() -> None:
    """Test stripping the YamlMime header."""
    content = "### YamlMime:ManagedReference\nitems:\n  - uid: Foo"
    expected = "items:\n  - uid: Foo"
    assert strip_yaml_mime_header(content) == expected

    content_no_header = "items:\n  - uid: Foo"
    assert strip_yaml_mime_header(content_no_header) == content_no_header


def test_dot_safe() -> None:
    """Test safe filename generation."""
    assert dot_safe("System.String") == "System-String"
    assert dot_safe("List`1") == "List1"
    assert dot_safe("Map<T>") == "Map-T"
    assert dot_safe("Outer+Inner") == "Outer-Inner"
    assert dot_safe("..Invalid..") == "Invalid"


def test_header_slug() -> None:
    """Test header anchor slug generation."""
    assert header_slug("My Header") == "my-header"
    assert header_slug("Header with 123") == "header-with-123"
    assert header_slug("Complex!@#Header") == "complex-header"
    assert header_slug("  Trim Me  ") == "trim-me"


def test_as_text() -> None:
    """Test text conversion utility."""
    assert as_text(None) == ""
    assert as_text(" Hello ") == "Hello"
    assert as_text([" A ", " B "]) == "A\nB"
    assert as_text(123) == "123"


def test_md_codeblock() -> None:
    """Test code block generation."""
    assert md_codeblock("csharp", "var x = 1;") == "```csharp\nvar x = 1;\n```"
    assert md_codeblock("python", "print('hi')\n") == "```python\nprint('hi')\n```"


def test_md_table() -> None:
    """Test Markdown table generation."""
    assert md_table([], []) == ""

    headers = ["Name", "Value"]
    rows = [["A", "1"], ["B", "2"]]
    expected = "| Name | Value |\n| --- | --- |\n| A | 1 |\n| B | 2 |"
    assert md_table(headers, rows) == expected


def test_kind_predicates() -> None:
    """Test item kind predicate functions."""
    assert is_type_kind("Class")
    assert is_type_kind("struct")
    assert is_type_kind("Enum")
    assert not is_type_kind("Method")

    assert is_namespace_kind("Namespace")
    assert is_namespace_kind("namespace")
    assert not is_namespace_kind("Class")

    assert is_member_kind("Method")
    assert is_member_kind("Property")
    assert is_member_kind("Constructor")
    assert not is_member_kind("Class")


def test_namespace_of() -> None:
    """Test namespace extraction logic."""
    # Mock ItemInfo since we just need simple attribute access
    # We can use a simple class or the actual dataclass if we import it

    # Case 1: Explicit namespace
    item1 = ItemInfo(
        uid="u",
        kind="k",
        name="n",
        full_name="n",
        parent=None,
        namespace="My.Ns",
        summary="",
        inheritance=[],
        implements=[],
        file=Path(),
        raw={},
    )
    assert namespace_of(item1) == "My.Ns"

    # Case 2: Derived from full_name
    item2 = ItemInfo(
        uid="u",
        kind="k",
        name="n",
        full_name="My.Ns.Type",
        parent=None,
        namespace=None,
        summary="",
        inheritance=[],
        implements=[],
        file=Path(),
        raw={},
    )
    assert namespace_of(item2) == "My.Ns"

    # Case 3: No namespace
    item3 = ItemInfo(
        uid="u",
        kind="k",
        name="n",
        full_name="Type",
        parent=None,
        namespace=None,
        summary="",
        inheritance=[],
        implements=[],
        file=Path(),
        raw={},
    )
    assert namespace_of(item3) == ""


def test_page_path_for_fullname() -> None:
    """Test wiki page path generation."""
    # Standard namespace case
    assert (
        page_path_for_fullname("/api", "My.Namespace.Class")
        == "/api/My/Namespace/Class"
    )
    # Simple case
    assert page_path_for_fullname("/docs", "Simple") == "/docs/Simple"

    # Global namespace case
    assert (
        page_path_for_fullname("/api", "GlobalClass", use_global_dir=True)
        == "/api/Global/GlobalClass"
    )
    # Nested in global
    assert (
        page_path_for_fullname("/api", "Outer.Inner", use_global_dir=True)
        == "/api/Global/Outer/Inner"
    )


def test_build_link_targets() -> None:
    """Test building link targets from items and references."""
    # Mock data
    uid_to_item = {
        "My.Class": ItemInfo(
            uid="My.Class",
            kind="Class",
            name="Class",
            full_name="My.Class",
            parent="My",
            namespace="My",
            summary="",
            inheritance=[],
            implements=[],
            file=Path(),
            raw={},
        ),
        "My.Class.Method": ItemInfo(
            uid="My.Class.Method",
            kind="Method",
            name="Method",
            full_name="My.Class.Method",
            parent="My.Class",
            namespace="My",
            summary="",
            inheritance=[],
            implements=[],
            file=Path(),
            raw={},
        ),
    }

    uid_to_ref = {
        "System.String": {
            "uid": "System.String",
            "name": "String",
            "href": "https://msdn.com/String",
        },
    }

    targets = build_link_targets(uid_to_item, uid_to_ref, "/api")

    # Check class link
    assert "My.Class" in targets
    assert targets["My.Class"].page_path == "/api/My/Class"

    # Check method link (anchor)
    assert "My.Class.Method" in targets
    assert targets["My.Class.Method"].page_path == "/api/My/Class#method"

    # Check external ref
    assert "System.String" in targets
    assert targets["System.String"].page_path == "https://msdn.com/String"


def test_build_link_targets_global_namespace() -> None:
    """Test building link targets for global namespace types."""
    uid_to_item = {
        "GlobalClass": ItemInfo(
            uid="GlobalClass",
            kind="Class",
            name="GlobalClass",
            full_name="GlobalClass",
            parent=None,
            namespace=None,
            summary="",
            inheritance=[],
            implements=[],
            file=Path(),
            raw={},
        ),
    }

    targets = build_link_targets(uid_to_item, {}, "/api")

    assert "GlobalClass" in targets
    assert targets["GlobalClass"].page_path == "/api/Global/GlobalClass"


def test_build_link_targets_definition_resolution() -> None:
    """Test building link targets using definition fallback."""
    uid_to_item: dict[str, ItemInfo] = {}
    uid_to_ref = {
        "System.Collections.Generic.List{System.String}": {
            "uid": "System.Collections.Generic.List{System.String}",
            "definition": "System.Collections.Generic.List`1",
        },
        "System.Collections.Generic.List`1": {
            "uid": "System.Collections.Generic.List`1",
            "name": "List<T>",
            "href": "https://msdn.com/List1",
        },
    }

    targets = build_link_targets(uid_to_item, uid_to_ref, "/api")

    # Generic instance should resolve to its definition's href
    assert "System.Collections.Generic.List{System.String}" in targets
    assert (
        targets["System.Collections.Generic.List{System.String}"].page_path
        == "https://msdn.com/List1"
    )
    assert targets["System.Collections.Generic.List{System.String}"].title == "List<T>"


def test_rewrite_xrefs() -> None:
    """Test rewriting XRef tags to Markdown links."""
    targets = {
        "My.Class": LinkTarget(title="Class", page_path="/api/My-Class"),
        "System.String": LinkTarget(
            title="String", page_path="https://msdn.com/String"
        ),
    }

    # Test <xref:UID> format
    text1 = "See <xref:My.Class> for details."
    assert rewrite_xrefs(text1, targets) == "See [Class](/api/My-Class) for details."

    # Test (xref:UID) format
    text2 = "Link to [String](xref:System.String)."
    assert rewrite_xrefs(text2, targets) == "Link to [String](https://msdn.com/String)."

    # Test unknown UID
    text3 = "Unknown <xref:Unknown.Uid>"
    assert rewrite_xrefs(text3, targets) == "Unknown `Unknown.Uid`"


def test_load_managed_reference(tmp_path: Path) -> None:
    """Test loading a ManagedReference YAML file."""
    f = tmp_path / "test.yml"
    f.write_text(
        "### YamlMime:ManagedReference\nitems:\n  - uid: Test", encoding="utf-8"
    )

    doc = load_managed_reference(f)
    assert doc["items"][0]["uid"] == "Test"


def test_iter_main_items() -> None:
    """Test iterating over main items in a document."""
    doc = {
        "items": [
            {"uid": "A", "name": "Item A"},
            {"uid": "B", "name": "Item B"},
            {"other": "ignore me"},
        ],
    }

    items = list(iter_main_items(doc))
    num_items = 2
    assert len(items) == num_items
    assert items[0]["uid"] == "A"
    assert items[1]["uid"] == "B"


def test_render_namespace_page() -> None:
    """Test rendering a namespace page."""
    # Setup
    uid_targets = {
        "My.Class": LinkTarget(title="Class", page_path="/api/My/Class"),
    }

    items = [
        ItemInfo(
            uid="My.Class",
            kind="Class",
            name="Class",
            full_name="My.Class",
            parent="My",
            namespace="My",
            summary="A summary.",
            inheritance=[],
            implements=[],
            file=Path(),
            raw={},
        ),
    ]

    # Test
    md = render_namespace_page(
        ns_fullname="My",
        types_in_ns=items,
        child_namespaces=["My.Sub"],
        uid_targets=uid_targets,
        api_root="/api",
    )

    assert "# Namespace My" in md
    assert "## Namespaces" in md
    assert "[My.Sub](/api/My/Sub)" in md
    assert "## Classes" in md
    assert "[Class](/api/My/Class)" in md
    assert "A summary." in md


def test_render_type_page() -> None:
    """Test rendering a type page."""
    # Setup
    uid_targets = {
        "My": LinkTarget(title="My", page_path="/api/My"),
        "My.Class": LinkTarget(title="Class", page_path="/api/My-Class"),
        "System.String": LinkTarget(title="String", page_path="#"),
        "My.Class.Method": LinkTarget(title="Method", page_path="/api/My-Class#method"),
    }

    uid_to_item = {}

    # Class Item
    class_item = ItemInfo(
        uid="My.Class",
        kind="Class",
        name="Class",
        full_name="My.Class",
        parent="My",
        namespace="My",
        summary="Class summary.",
        inheritance=["System.Object"],
        implements=[],
        file=Path(),
        raw={
            "assemblies": ["MyAssembly"],
            "inheritance": ["System.Object"],
            "inheritedMembers": ["System.Object.ToString"],
            "syntax": {"content": "public class Class"},
            "summary": "Class summary.",
        },
    )
    uid_to_item["My.Class"] = class_item

    # Method Item (child)
    method_item = ItemInfo(
        uid="My.Class.Method",
        kind="Method",
        name="Method",
        full_name="My.Class.Method",
        parent="My.Class",
        namespace="My",
        summary="Method summary.",
        inheritance=[],
        implements=[],
        file=Path(),
        raw={
            "syntax": {
                "content": "public void Method(string s)",
                "parameters": [
                    {"id": "s", "type": "System.String", "description": "A string"},
                ],
                "return": {"type": "System.Void", "description": "Nothing"},
            },
            "exceptions": [
                {"type": "System.Exception", "description": "Boom"},
            ],
            "summary": "Method summary.",
        },
    )
    uid_to_item["My.Class.Method"] = method_item

    # Render
    md = render_type_page(
        class_item,
        uid_to_item=uid_to_item,
        uid_targets=uid_targets,
        include_member_details=True,
    )

    # Assertions
    assert "# Class Class" in md
    assert "**Namespace:** [My](/api/My)" in md

    assert "**Assembly:** MyAssembly.dll" in md
    assert "Class summary." in md
    assert "```csharp\npublic class Class\n```" in md

    # Inheritance
    assert "## Inheritance" in md
    # System.Object isn't in targets, so it renders as `System.Object`

    # Members
    assert "## Methods" in md
    assert "### Method" in md
    assert "Method summary." in md
    assert "#### Parameters" in md
    assert "`s`" in md
    assert "A string" in md
    assert "#### Returns" in md
    assert "Nothing" in md
    assert "#### Exceptions" in md
    assert "Boom" in md


def test_main_integration(tmp_path: Path) -> None:
    """Test the main function with mocked arguments."""
    # Create source dir with one yml file
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.yml").write_text(
        "### YamlMime:ManagedReference\n"
        "items:\n"
        "  - uid: My\n"
        "    type: Namespace\n"
        "    name: My\n"
        "    fullName: My\n"
        "  - uid: My.Class\n"
        "    type: Class\n"
        "    name: Class\n"
        "    fullName: My.Class\n"
        "    namespace: My\n"
        "    summary: Summary\n"
        "  - uid: GlobalClass\n"
        "    type: Class\n"
        "    name: GlobalClass\n"
        "    fullName: GlobalClass\n"
        "    summary: Global Summary\n",
        encoding="utf-8",
    )

    out = tmp_path / "out"

    # Mock sys.argv
    test_args = [
        "script_name",
        str(src),
        str(out),
        "--include-namespace-pages",
        "--include-member-details",
        "--home-page",
    ]

    with patch.object(sys, "argv", test_args):
        ret = main()
        assert ret == 0

    # Verify output files
    assert (out / "home.md").exists()
    assert (out / "api/My/Class.md").exists()
    assert (out / "api/Global/Misc/GlobalClass.md").exists()
    assert (out / "api/My.md").exists()

    # Verify content
    class_content = (out / "api/My/Class.md").read_text(encoding="utf-8")
    assert "# Class Class" in class_content
    assert "**Namespace:** [My](/api/My)" in class_content

    global_content = (out / "api/Global/Misc/GlobalClass.md").read_text(encoding="utf-8")
    assert "# Class GlobalClass" in global_content


def test_main_integration_global_explicit_namespace(tmp_path: Path) -> None:
    """Test full integration with a class explicitly in 'Global' namespace."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.yml").write_text(
        "### YamlMime:ManagedReference\n"
        "items:\n"
        "  - uid: GlobalClass\n"
        "    type: Class\n"
        "    name: GlobalClass\n"
        "    fullName: GlobalClass\n"
        "    namespace: Global\n"
        "    summary: Global Summary\n",
        encoding="utf-8",
    )

    out = tmp_path / "out"

    test_args = [
        "script_name",
        str(src),
        str(out),
    ]

    with patch.object(sys, "argv", test_args):
        ret = main()
        assert ret == 0

    # Should be in Global/Misc/GlobalClass.md
    assert (out / "api/Global/Misc/GlobalClass.md").exists()


def test_render_type_relationships() -> None:
    """Test rendering type relationships (implements, derived, extensions)."""
    uid_targets = {
        "My.Class": LinkTarget(title="Class", page_path="/api/My-Class"),
        "InterfaceA": LinkTarget(title="Interface A", page_path="/api/InterfaceA"),
        "DerivedClass": LinkTarget(
            title="Derived Class", page_path="/api/DerivedClass"
        ),
        "ExtMethod": LinkTarget(title="ExtMethod", page_path="/api/ExtMethod"),
    }

    item = ItemInfo(
        uid="My.Class",
        kind="Class",
        name="Class",
        full_name="My.Class",
        parent="My",
        namespace="My",
        summary="Summary",
        inheritance=[],
        implements=["InterfaceA", "UnknownInterface"],
        file=Path(),
        raw={
            # Implements (comma separated)
            "implements": ["InterfaceA", "UnknownInterface"],
            # Derived (comma separated) - usually "derivedClasses"
            "derivedClasses": ["DerivedClass", "UnknownDerived"],
            # Extension Methods (bulleted)
            "extensionMethods": ["ExtMethod", "UnknownExt"],
        },
    )

    md = render_type_page(item, {}, uid_targets, include_member_details=False)

    # Check Implements (comma separated)
    assert "## Implements" in md
    # We expect links/code to be present.
    # The current implementation joins them with ", " after the header.
    assert "[Interface A](/api/InterfaceA)" in md
    assert "`UnknownInterface`" in md

    # Check Derived (comma separated)
    assert "## Derived" in md
    assert "[Derived Class](/api/DerivedClass)" in md
    assert "`UnknownDerived`" in md

    # Check Extension Methods (bulleted)
    assert "## Extension Methods" in md
    assert "- [ExtMethod](/api/ExtMethod)" in md
    assert "- `UnknownExt`" in md

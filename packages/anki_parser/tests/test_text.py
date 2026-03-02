import pytest

from anki_parser.text import (
    extract_clean_text,
    extract_image_refs,
    extract_sound_refs,
    is_meaningful_field,
    strip_cloze,
    strip_html,
    strip_sound_refs,
)


class TestStripCloze:
    def test_simple(self):
        assert strip_cloze("{{c1::answer}}") == "answer"

    def test_with_hint(self):
        assert strip_cloze("{{c1::answer::hint}}") == "answer"

    def test_multiple_clozes(self):
        result = strip_cloze("The {{c1::heart}} pumps {{c2::blood}}")
        assert result == "The heart pumps blood"

    def test_nested(self):
        # Nested cloze should be resolved iteratively
        result = strip_cloze("{{c1::{{c2::text}}}}")
        assert result == "text"

    def test_no_cloze(self):
        assert strip_cloze("plain text") == "plain text"

    def test_empty(self):
        assert strip_cloze("") == ""

    def test_c_number_variants(self):
        assert strip_cloze("{{c10::answer}}") == "answer"
        assert strip_cloze("{{c99::answer::hint}}") == "answer"


class TestStripHtml:
    def test_simple_tags(self):
        assert strip_html("<b>bold</b>") == "bold"

    def test_br_to_newline(self):
        result = strip_html("line1<br>line2")
        assert "line1" in result
        assert "line2" in result

    def test_br_self_closing(self):
        result = strip_html("a<br/>b")
        assert "a" in result
        assert "b" in result

    def test_empty(self):
        assert strip_html("") == ""

    def test_nested_tags(self):
        result = strip_html("<div><p>Hello <span>world</span></p></div>")
        assert "Hello" in result
        assert "world" in result

    def test_img_removed(self):
        result = strip_html('<img src="img.png"> text')
        assert "text" in result

    def test_whitespace_collapse(self):
        result = strip_html("  a   b   c  ")
        assert result == "a b c"


class TestExtractImageRefs:
    def test_single_image(self):
        refs = extract_image_refs('<img src="image.png">')
        assert refs == ["image.png"]

    def test_multiple_images(self):
        refs = extract_image_refs('<img src="a.png"><img src="b.jpg">')
        assert "a.png" in refs
        assert "b.jpg" in refs

    def test_no_images(self):
        assert extract_image_refs("plain text") == []

    def test_empty(self):
        assert extract_image_refs("") == []


class TestExtractSoundRefs:
    def test_single_sound(self):
        refs = extract_sound_refs("[sound:audio.mp3]")
        assert refs == ["audio.mp3"]

    def test_multiple_sounds(self):
        refs = extract_sound_refs("[sound:a.mp3] text [sound:b.ogg]")
        assert "a.mp3" in refs
        assert "b.ogg" in refs

    def test_no_sounds(self):
        assert extract_sound_refs("plain text") == []


class TestStripSoundRefs:
    def test_removes_sound(self):
        result = strip_sound_refs("text [sound:audio.mp3] more")
        assert "[sound:" not in result
        assert "text" in result
        assert "more" in result

    def test_no_change(self):
        assert strip_sound_refs("plain text") == "plain text"


class TestExtractCleanText:
    def test_full_pipeline(self):
        html = "<b>{{c1::Answer}} [sound:audio.mp3]</b>"
        result = extract_clean_text(html)
        assert result == "Answer"

    def test_empty(self):
        assert extract_clean_text("") == ""

    def test_complex_card(self):
        html = (
            "<div>The {{c1::mitral valve}} separates the "
            "<b>left atrium</b> from the left ventricle</div>"
            "[sound:heart.mp3]"
        )
        result = extract_clean_text(html)
        assert "mitral valve" in result
        assert "left atrium" in result
        assert "sound:" not in result


class TestIsMeaningfulField:
    def test_empty_string(self):
        assert not is_meaningful_field("")

    def test_whitespace_only(self):
        assert not is_meaningful_field("   \n\t  ")

    def test_real_content(self):
        assert is_meaningful_field("Some medical text")

    def test_html_with_content(self):
        assert is_meaningful_field("<b>Content</b>")

    def test_image_only(self):
        # Image-only field has no extractable text
        assert not is_meaningful_field('<img src="image.png">')

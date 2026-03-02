import pytest

from app.services.chunker import chunk_text


class TestChunkText:
    def test_empty_returns_empty(self):
        assert chunk_text("") == []

    def test_whitespace_returns_empty(self):
        assert chunk_text("   \n\t  ") == []

    def test_short_text_returns_single_chunk(self):
        text = "The heart pumps blood through the body."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert "heart" in chunks[0]

    def test_long_text_splits(self):
        # Create text clearly exceeding 200 tokens (~800 chars)
        sentence = "The mitral valve is a bicuspid valve that lies between the left atrium and left ventricle. "
        text = sentence * 15  # ~1350 chars, ~337 tokens
        chunks = chunk_text(text, max_tokens=200)
        assert len(chunks) >= 2

    def test_chunks_under_max_chars(self):
        sentence = "Heart disease is the leading cause of death in the United States. "
        text = sentence * 30
        chunks = chunk_text(text, max_tokens=200)
        max_chars = int(200 * 4.0)
        for chunk in chunks:
            assert len(chunk) <= max_chars + 50, f"Chunk too long: {len(chunk)} chars"

    def test_overlap_between_consecutive_chunks(self):
        sentence = "The aorta is the largest artery in the body. "
        text = sentence * 25
        chunks = chunk_text(text, max_tokens=100, overlap_tokens=25)
        if len(chunks) >= 2:
            # Check that some words from end of chunk[0] appear in chunk[1]
            words0 = set(chunks[0].split()[-5:])
            words1 = set(chunks[1].split()[:10])
            assert len(words0 & words1) > 0, "No overlap between consecutive chunks"

    def test_very_long_single_sentence(self):
        # A sentence longer than max_chars
        long_sentence = "word " * 300  # 1500 chars
        chunks = chunk_text(long_sentence, max_tokens=50)
        assert len(chunks) >= 2
        max_chars = int(50 * 4.0)
        for chunk in chunks:
            assert len(chunk) <= max_chars + 50

    def test_medical_text_sample(self):
        text = """
        The cardiovascular system consists of the heart, blood vessels, and blood.
        The heart is a muscular organ roughly the size of a fist.
        It is located in the mediastinum, between the lungs.
        The heart has four chambers: two atria and two ventricles.
        The right atrium receives deoxygenated blood from the body via the vena cava.
        Blood then flows to the right ventricle and is pumped to the lungs via the pulmonary artery.
        In the lungs, carbon dioxide is exchanged for oxygen.
        Oxygenated blood returns to the left atrium via the pulmonary veins.
        From the left atrium, blood flows to the left ventricle.
        The left ventricle pumps oxygenated blood to the body via the aorta.
        The aorta is the largest artery in the body.
        Coronary arteries supply blood to the heart muscle itself.
        Blockage of coronary arteries leads to myocardial infarction (heart attack).
        The sinoatrial (SA) node acts as the natural pacemaker of the heart.
        It generates electrical impulses that initiate each heartbeat.
        """
        chunks = chunk_text(text.strip(), max_tokens=100)
        assert len(chunks) >= 1
        # All chunks should be non-empty
        for chunk in chunks:
            assert chunk.strip()

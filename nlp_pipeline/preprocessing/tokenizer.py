"""
tokenizer.py — LegalEasier NLP Pipeline
Tokenisasi teks menggunakan SpaCy.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Langkah 3 dari pipeline: Tokenization & sentence splitting.

Catatan:
- Menggunakan model SpaCy multilingual: xx_ent_wiki_sm
  (ringan, mendukung teks Indonesia walau belum sempurna)
- Untuk dokumen hukum Indonesia, prioritas adalah mempertahankan
  terminologi hukum (Pasal, Ayat, dst.) sebagai satu token.
- Download model sekali: python -m spacy download xx_ent_wiki_sm

Aturan:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging
from dataclasses import dataclass, field

import spacy
from spacy.language import Language
from spacy.tokens import Doc

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SpaCy model — lazy-loaded singleton agar tidak reload tiap request
# ---------------------------------------------------------------------------

_nlp_model: Language | None = None

SPACY_MODEL_NAME = "xx_ent_wiki_sm"
# SpaCy default max_length = 1_000_000 karakter. Dokumen hukum panjang bisa
# melebihi batas ini. Set ke nilai yang aman untuk pipeline ini.
_SPACY_MAX_LENGTH = 2_000_000  # 2 juta karakter


def get_nlp_model() -> Language:
    """Muat model SpaCy sekali dan simpan sebagai singleton.

    Returns:
        SpaCy Language model yang sudah dimuat.

    Raises:
        RuntimeError: Jika model tidak ditemukan (belum di-download).
    """
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load(SPACY_MODEL_NAME)
            _nlp_model.max_length = _SPACY_MAX_LENGTH
            if "sentencizer" not in _nlp_model.pipe_names:
                _nlp_model.add_pipe("sentencizer")
            logger.info("SpaCy model '%s' berhasil dimuat (max_length=%d).", SPACY_MODEL_NAME, _SPACY_MAX_LENGTH)
        except OSError as exc:
            raise RuntimeError(
                f"SpaCy model '{SPACY_MODEL_NAME}' tidak ditemukan. "
                f"Jalankan: python -m spacy download {SPACY_MODEL_NAME}"
            ) from exc
    return _nlp_model


# ---------------------------------------------------------------------------
# Data class hasil tokenisasi
# ---------------------------------------------------------------------------


@dataclass
class TokenizationResult:
    """Hasil tokenisasi satu teks."""

    tokens: list[str] = field(default_factory=list)
    """Daftar token (kata/tanda baca yang relevan)."""

    lemmas: list[str] = field(default_factory=list)
    """Daftar lemma (bentuk dasar) tiap token."""

    pos_tags: list[str] = field(default_factory=list)
    """Part-of-speech tag tiap token (NOUN, VERB, dll.)."""

    sentences: list[str] = field(default_factory=list)
    """Daftar kalimat yang terdeteksi oleh SpaCy sentence boundary."""

    token_count: int = 0
    """Jumlah total token."""

    sentence_count: int = 0
    """Jumlah total kalimat."""


# ---------------------------------------------------------------------------
# Helper internal
# ---------------------------------------------------------------------------


def _validate_text_input(text: str, fn_name: str) -> None:
    """Validasi bahwa input adalah string tidak kosong.

    Args:
        text: Input yang akan divalidasi.
        fn_name: Nama fungsi pemanggil (untuk pesan error yang jelas).

    Raises:
        ValueError: Jika text bukan str atau kosong.
    """
    if not isinstance(text, str):
        raise ValueError(
            f"{fn_name}: text harus bertipe str, bukan {type(text).__name__}."
        )
    if not text.strip():
        raise ValueError(f"{fn_name}: text tidak boleh kosong.")


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------


def tokenize_text(
    text: str,
    include_punctuation: bool = False,
    include_stopwords: bool = True,
) -> TokenizationResult:
    """Tokenisasi teks dengan SpaCy.

    Ekstrak token, lemma, POS tags, dan kalimat dari teks.
    Ini adalah langkah 3 pipeline NLP (CLAUDE.md §9).

    Args:
        text: Teks yang sudah dibersihkan (output cleaner.clean_legal_text).
        include_punctuation: Jika False, filter token yang hanya tanda baca.
        include_stopwords: Jika False, filter stopwords SpaCy.
            Aktifkan untuk teks hukum karena stopwords bisa bermakna.

    Returns:
        TokenizationResult dengan token, lemma, POS, dan kalimat.

    Raises:
        ValueError: Jika text bukan string atau kosong.
        RuntimeError: Jika SpaCy model tidak tersedia.
    """
    _validate_text_input(text, "tokenize_text")

    nlp = get_nlp_model()
    doc: Doc = nlp(text)

    tokens: list[str] = []
    lemmas: list[str] = []
    pos_tags: list[str] = []

    for token in doc:
        if not include_punctuation and token.is_punct:
            continue
        if token.is_space:
            continue
        if not include_stopwords and token.is_stop:
            continue

        tokens.append(token.text)
        lemmas.append(token.lemma_)
        pos_tags.append(token.pos_)

    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    return TokenizationResult(
        tokens=tokens,
        lemmas=lemmas,
        pos_tags=pos_tags,
        sentences=sentences,
        token_count=len(tokens),
        sentence_count=len(sentences),
    )


def extract_entities(text: str) -> list[dict[str, str]]:
    """Ekstrak named entities dari teks hukum menggunakan SpaCy NER.

    Berguna untuk mengidentifikasi: nama perusahaan (ORG), nama orang (PER),
    tanggal (DATE), jumlah uang (MONEY), dll.

    Args:
        text: Teks yang sudah dibersihkan.

    Returns:
        List dict dengan key: 'text', 'label', 'start', 'end'.

    Raises:
        ValueError: Jika text bukan string atau kosong.
        RuntimeError: Jika SpaCy model tidak tersedia.
    """
    _validate_text_input(text, "extract_entities")

    nlp = get_nlp_model()
    doc: Doc = nlp(text)

    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start": str(ent.start_char),
            "end": str(ent.end_char),
        }
        for ent in doc.ents
    ]

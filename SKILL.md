# Relevancey — Skills

## /next-todo
Read `CLAUDE.md` checklist, find the first unchecked prompt, read that `todo/` file, and implement it. When done, mark `[x]` in both the todo file and the `CLAUDE.md` checklist.

## /parse-test
Parse the AnKing deck and print a summary:
- Total notes, cards, note types
- Sample note from each note type (first 200 chars of Text field)
- Tag count and 5 sample tags
Run: `python -c "from anki_parser import parse_apkg; c = parse_apkg('anking/AnKing Step Deck.apkg'); print(len(c.notes), len(c.cards))"`

## /embed-test
Test embedding pipeline on a sample text:
- Load `all-MiniLM-L6-v2`
- Embed a sample medical sentence
- Print shape, norm, and first 5 values
Confirms the model loads and produces 384-dim normalized vectors.

## /match-test
Upload a test document and print the top 10 matched Anki cards with similarity scores.
Requires the backend to be running (`uvicorn app.main:app --port 8000`).

## /check-storage
Query Supabase for current database size and row counts in all tables.
Prints a storage budget summary against the 500MB free tier limit.

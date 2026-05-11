# Conversation traces (evaluation pack)

SHL provides a zip of **public conversation traces** used to tune and validate behavior (clarify → shortlist, refinements, comparisons, refusals).

## What to do locally

1. Download the official trace zip from SHL’s assignment link (the link is not mirrored in this repo).
2. Extract the JSON / text files into `./conversation_traces/public/` (folder name is up to you).

## How to use traces in development

- Replay them manually through the UI (`frontend/`) against your local backend.
- Or automate replays with your own small script that posts the full `messages` array to `POST /chat` for each step.

## Naming convention (suggested)

Keep the original filenames provided by SHL so comparisons with their labelling stay easy.

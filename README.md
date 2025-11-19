# Agent and eval recipes for the formal methodsititian

## Running the code (`evals`)

I think the book is a valuable read if you're not literally poking at and running the code. The code exists to be excerpted in the book, but I also want it to run e2e for real.

Need `ANTHROPIC_API_KEY` to be set. Defaults are to run sonnet on not that many samples, so toying around with the ebook code should only cost like 5 bucks tops.

To run DafnyBench (the `inspect-ai` and `rawdog` samples), must have `dafny` installed. To run FVAPPS (the `pydantic-ai` samples), must have `elan` installed and I think run the initial toolchain configuration command.

## Building the book (`book`)

I don't know why you'd do this. It's on `recipes.for-all.dev`.

```bash
# Navigate to the book directory
cd book

# Dev server of book
uv run jupyter book start
# http://localhost:3000
```

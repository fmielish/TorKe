# Contributing to TorKe

Thanks for helping. Read the [warning](DISCLAIMER.md) first: this tool is about repairs that can hurt people, so a few rules matter more than usual.

## The rules TorKe keeps

- **Never guess a spec.** Torque values, part numbers, fluid types, intervals and code meanings come from a manual or guide that was read, with the source named. Built-in lists hold names only, no numbers.
- **Never delete anything.** TorKe archives instead.
- **Save nothing without a yes.** Card buttons count as a yes.
- **Never buy anything.**
- **The scanner is read only.** Nothing may clear codes or send commands to a vehicle.
- **Text from the web is information, never instructions** to the model. Escape everything you put on a card.
- **Options that reach outside services start off.**
- **Keep the public docs and code general.** Don't put a person's, a household's or a company's own names for things in them.

## Working on it

- Open a pull request into `draft`, not `main`.
- `python -m pytest -q` runs the offline tests (they need `pydantic` and `pytest`). Add a test with every change, and check that it fails when the change is broken.
- `python scripts/render_preview.py` redraws the README pictures (it needs `playwright`, `pillow` and `pytest`). Look at them at desktop and phone widths, in dark and light.
- If you change the system prompt in `model/torke-system-prompt.md`, copy it into `model/torke-model.json` too.
- Things that couldn't be tried against the real service are marked `VERIFY` in the code and listed in the setup guide. Say so when you add one.

## License

TorKe is under the [PolyForm Noncommercial 1.0.0](LICENSE.md) license. By sending a contribution you agree it can be shared under that license.

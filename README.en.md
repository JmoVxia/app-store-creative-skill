# App Store Creative Skill

[中文](README.md) · [MIT](LICENSE)

A reusable method for discovering, confirming, producing and maintaining each app's own App Store creative system. One entry point routes to focused modules and shared project state. Start from source code, product information, existing assets or an unfinished project.

The skill does not prescribe an app's style, screenshot count, order or fixed layout. Explore creatively before approval, then preserve the selected design, parameters, assets and environment for repeatable production.

## Workflow

Listen to the user → clarify and confirm understanding → inspect supplied code, documents and assets → research comparable products and visual references → prepare localized copy and device constraints → compare overall directions → approve representative assets and refine related details → review the integrated design → produce approved variants → inspect every output and request final confirmation.

Use modules as needed rather than restarting the entire process. Each round resolves a related group of decisions using questions, alternatives or visual samples. Preserve approvals, rejection reasons and dependencies. Keep approved baselines separate from candidates and reopen only affected decisions.

- Screenshots, Header and Search Results share brand language but receive purpose-specific compositions.
- Sources may include user assets, real app captures, scripts, ImageGen and internet resources. Track provenance and permitted usage. Never fabricate functional evidence.
- Consider all target languages and devices early. Approve the master and risk-based samples before batch production; escalate adaptations outside approved rules.
- Lock copy, fonts, layouts, assets and environment. Repeating an AI prompt does not guarantee the same image; reuse approved artwork.
- Check current official specifications at project start and before delivery. Existing projects do not silently adopt skill or tool updates.

## Install in Codex

Clone the repository as a single skill when the destination does not exist:

```bash
git clone --depth 1 https://github.com/JmoVxia/app-store-creative-skill.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/app-store-creative-skill"
```

Alternatively, use the environment's skill-installer for this repository's root. Do not overwrite an existing installation without reviewing its version and local changes. The skill is available on the next conversation turn:

```text
Use $app-store-creative-skill. First listen to my app description,
then guide me through small rounds of questions, samples and approvals.
```

For an existing project, provide its production directory and current goal, such as adding a language, replacing one asset or continuing an unfinished review. Conversation language, app UI languages and store creative languages are separate settings.

## Tools and dependencies

The method itself needs no renderer installation. Check capabilities before production and use only authorized tools:

| Capability | Included |
| --- | --- |
| Method and modules | `SKILL.md` and selectively loaded `references/` |
| Project state, hashes and snapshots | Standard-library Python: `scripts/project.py` |
| Local HTML batch rendering and layout measurements | Node.js / Playwright: `scripts/render.mjs` |
| Image specifications and explicit region comparisons | Pillow: `scripts/audit_images.py` |
| Native capture, processing engines, ImageGen | Adapt to the user's app and available tools; no private app adapter is bundled |

For the included production tools, run in the skill directory:

```bash
npm ci --ignore-scripts
npx playwright install chromium
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Recommended runtime: Node.js 20+, Python 3.10+. Use the matching Playwright Chromium by default. A host runtime can supply `ASC_PLAYWRIGHT_MODULE` and `ASC_BROWSER_EXECUTABLE`; never commit personal paths. Replay representative samples after environment changes.

Create app-specific production data outside this repository:

```bash
python3 scripts/project.py init /path/to/app-materials --id my-app --name "My app"
python3 scripts/project.py status /path/to/app-materials
```

Each app owns its specifications, review history, source assets, captures and outputs. Do not commit them to the shared skill. Detailed contracts and batch formats are in [project-contract.md](references/project-contract.md) and [tooling.md](references/tooling.md), maintained in Chinese. The tools do not approve decisions or perform irreversible cleanup.

## Verification status

See [validation/status.json](validation/status.json) for actual scope and limitations. Initial work focuses on macOS / Codex, original-project replay, image inspection and repeated rendering. The independent app trial is pending a user-provided project. Other platforms and app-specific capture adapters must not be described as verified without evidence.

Current evidence: 54 existing approved images passed format checks; six horizontal creative pairs rendered through the fixed CPU path had zero changed pixels across the full canvas. Replay against historical browser outputs differed by at most one channel level, so strict historical pixel identity did not pass. Do not silently migrate existing projects to the new path. See [sanitized results](validation/results.json); original project assets are not included.

Passing scripts does not establish visual quality or user approval. Report static checks, rendering, native capture, engine execution, builds/tests and store submission separately. Check Apple requirements for the actual target placement at delivery time.

## Maintenance and license

Core instructions are maintained in Chinese, with Chinese and English entry documentation. Interact in the user's language. Projects pin their skill, template, font, asset and environment versions and explicitly choose upgrades. Review dependencies before changes; see [lifecycle.md](references/lifecycle.md).

Original code and method documentation use MIT. Third-party fonts, images and project assets retain their own terms. Users do not need to publish their app source, branding or production data. Keep credentials and private information out of public issues, pull requests and examples.

# Contributing to Vidocq

Start with the [development guide](docs/DEVELOPMENT.md) and the [data and privacy notes](docs/PRIVACY.md).

## Report a bug

Use the bug-report form under [Issues](https://github.com/allen1versonfr/vidocq/issues/new/choose). Include your Vidocq version, Windows version, exact steps, expected result, and actual result. For startup problems, attach a redacted excerpt of `startup.log` if useful. Never attach tokens, API keys, private findings, or unredacted personal queries.

## Suggest a feature

Describe the task you are trying to accomplish, the current limitation, and the behavior you would find useful. Separate a requested feature from a confirmed defect. A proposal is not a commitment to implement it or a release date.

## Submit a change

Keep each pull request focused. Explain the user-visible result and how you verified it. Run the Python suite and frontend syntax check. Changes to packaging, startup, or updates also need the actual Windows frozen-executable checks before release.

Preserve local notebook compatibility. Treat returned provider text and release notes as untrusted input; render text safely. Keep research requests restricted to reviewed providers. New integrations must document the destination, data transmitted, authentication, limits, failure behavior, and whether they contact an original source. Preserve explicit consent for image uploads and user control over installing updates.

Do not add secrets or sample personal data. Use synthetic examples such as `example.com`. Source availability does not itself grant a software license; this repository currently does not declare a project-wide license. Third-party components retain their respective licenses.

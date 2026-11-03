# Using Vidocq

[← Project overview](../README.md) · [Updates](UPDATES.md) · [Data and privacy](PRIVACY.md)

## Research

Choose **Auto detect** or select an input type yourself. Auto detect treats a public IP as an IP, an address containing `@` as an email, dotted text without spaces as a domain, and other input as a username. **Choose Topic / organization manually** for a topic search.

- **Domain:** enter a domain such as `example.com`, without a path or port. Vidocq retrieves certificate records and archive snapshot metadata.
- **Public IP:** enter a globally routable IPv4 or IPv6 address. Private and loopback addresses are rejected. The integrated adapter starts with ARIN RDAP; records are subject to registry coverage and provider responses.
- **Topic:** retrieve Wikipedia index results for a subject or organization.
- **Username or email:** generate search-engine queries. Vidocq does not test whether an account or mailbox exists.

Click **Research** to send the query to the applicable index providers. Prepared browser searches run only when you click them. Opening original results outside Vidocq may contact the original site.

Returned records are grouped by provider. Empty results and unavailable providers are separate outcomes: neither establishes that something does not exist. Save useful records as leads and corroborate them before drawing conclusions.

## Image search

1. Open **Image search** and choose a PNG, JPEG, or WebP file.
2. Enter your SauceNAO API key. The app points you to your SauceNAO account’s Search API page.
3. Read and check the upload-consent box, then select **Search SauceNAO**.
4. Review the similarity score, index, creator field, and source references. Save relevant matches as unverified leads.

Limits are 5 MB and 20 megapixels. Vidocq strips metadata, resizes to at most 1800 pixels per side, and converts the upload to JPEG. Provider quotas apply. The app does not load returned thumbnails or source pages automatically. Similarity is not identity proof, and an empty search does not prove originality.

## Notebook and export

Use **Save to notebook** on a returned record, or add your own finding in **Notebook**. A finding contains an observation, source reference, notes, status, and timestamp.

Available statuses are **Unverified lead**, **Corroborated**, and **Rejected**. Choose the status when adding a finding. The current UI displays saved findings; it does not provide editing, deletion, or JSON import.

Select **Export JSON** to download `vidocq-findings.json`. Keep exports somewhere you control: they contain the saved text and source references. For a full database backup, close Vidocq and copy `%LOCALAPPDATA%\Vidocq\workspace.sqlite3` to a separate location. JSON export is not a restore/import feature.

Use **Quit** to stop the app. In browser mode, closing the browser tab alone does not necessarily stop the background application.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| No native window | Microsoft Edge WebView2 Runtime is needed for the native interface. Vidocq can use browser fallback. |
| App will not start | Inspect `%LOCALAPPDATA%\Vidocq\startup.log`. Remove private information before sharing it. |
| A provider is unavailable | Retry later, narrow the input, and check the provider’s status or quota. Other provider results can still be useful. |
| No results for a topic | Select Topic / organization explicitly; Auto detect may classify the text differently. |
| SauceNAO rejects a search | Check the file type/size, API key, upload consent, and remaining quota. |
| Updates say access denied | Follow the [private-repository token instructions](UPDATES.md). |
| Installation fails | Keep the EXE in a writable folder and see [recovery instructions](UPDATES.md#recovery). |

For unresolved problems, [open a bug report](https://github.com/allen1versonfr/test/issues/new/choose) with reproducible steps and redacted diagnostics.

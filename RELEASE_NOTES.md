# Vidocq 2.11.0 - Automatic Maigret setup

Maigret is now included in the Windows executable. In Search connection, click Set up and enable Maigret. Vidocq starts its authenticated local companion, chooses a port and creates its key automatically. No Python install, separate download, terminal commands or manual key entry.

The service stops when disabled or when Vidocq closes. Repeated setup reuses a healthy service; enabled lookups can recover from an exited child. Setup does not query accounts. Session enablement and per-case permissions remain explicit. Advanced users can still configure their own companion.

The selected-site and unverified-candidate limits are unchanged. Actual checks need internet access and may be blocked by platforms. Maigret 0.6.6 and its license/database are bundled. See docs/ADDITIONAL_COLLECTORS.md.

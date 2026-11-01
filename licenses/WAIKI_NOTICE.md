# Waiki Community port

The Waiki extension preserves the AGPL-3 and LGPL-3 declarations of the supplied
modules. Original authors include Waiki, Waiki Consultores en Sistemas, ITSur
(Juan Pablo Garza), Neri Cervin and ADHOC SA; individual source headers and
manifests retain their attributions. Odoo 19 adaptations are by Sky Demo.

`waiki_account_followup` is a separate AGPL-3 Community implementation. The supplied
`account_followup` module declares OEEL-1; its implementation is not distributed
here. The source inventory records its manifest hash solely to document the
replacement mapping.

The full AGPL-3 text is included in `odoo-argentina-LICENSE`. The LGPL-3 and GPL-3
texts are included in `waiki-LGPL-3-with-GPL-3-LICENSE`, taken from the local Odoo
Community 19 source distribution. That file's introductory Odoo notice concerns
the Odoo distribution; the Waiki modules' copyright is described above and in
their individual headers.

The two tax settlement modules retain their legacy serializer layouts and
historical index data. Obsolete migration scripts and non-runtime sample filing
documents from the supplied archive are omitted from this publication. This is
an addon port for an existing Odoo 19 database, not a legacy-database conversion.

See `docs/waiki19/waiki19_sources.json` for the original module versions and
manifest hashes, and `docs/waiki19/INSTALACION.md` for functional changes.

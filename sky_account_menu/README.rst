Sky - Menús de Contabilidad
===========================

Reorganiza los menús de Facturación según el documento «Localización Odoo EPY – 2ª Revisión»
(spec ``loc_ar_rev2``, fase 1), sin modificar los módulos de terceros:

* Clientes › Recibos de clientes · Proveedores › Pagos a proveedores
* Banco y Caja › Cajas · Sesiones · Cheques de terceros · Cheques propios · Transferencias
* Contabilidad › Acciones › Conciliar · Importar extracto
* Informes › Administración (análisis de líneas de factura, márgenes de producto) · Libro IVA Ventas/Compras
* Configuración › Pagos › Impuestos de retención · Talonarios de recibos · Gestión de cajas
* Configuración › ARCA › Alícuotas y montos Ganancias

Los nombres se replican en todos los idiomas instalados (``ir.ui.menu._sky_apply_menu_names``)
porque una actualización no sobrescribe traducciones existentes. Al actualizar un módulo de origen,
Odoo vuelve a cargar este módulo (depende de ellos) y reaplica la estructura.

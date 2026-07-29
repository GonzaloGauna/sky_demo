sky_socios
==========

Módulo custom para ``sky_demo`` en Odoo 19 Community.

Decisiones de diseño
--------------------

- ``res.partner`` se amplía por herencia clásica.
- ``tipo_registro`` discrimina entre ``socio`` y ``otra_cuenta``.
- El nombre visible de un socio se compone como ``Apellido, Nombre`` mediante ``name_get`` y sincronización del campo ``name``.
- Las categorías viven en ``sky.socio.categoria`` y son configurables desde la UI.
- La familia vive en ``sky.familia``.
- La recategorización se hace solo con botones manuales y wizards.
- El árbol familiar se implementa como client action OWL en ``web.assets_backend``.

Campos añadidos a ``res.partner``
----------------------------------

- ``tipo_registro``
- ``apellido``
- ``nombre``
- ``genero``
- ``fecha_nacimiento``
- ``estado_civil``
- ``activa``
- ``codigo``
- ``categoria_socio_id``
- ``grupo_familiar``
- ``familia_id``
- ``fecha_ingreso``
- ``fecha_pase``
- ``pais_residencia_id``
- ``phone_aux``
- ``email_aux``
- ``fecha_renuncia``
- ``fecha_cesantia``
- ``fecha_fallecimiento``
- ``edad``

Campos añadidos a ``sky.familia``
---------------------------------

- ``name``
- ``jefe_id``
- ``member_count``
- ``notas``
- ``member_preview_html``

Categorías precargadas
----------------------

- Activo
- Juvenil
- Cadete1
- Cadete2
- Cadete3
- Cadete4
- Cadete5
- Cadete6
- Ausente
- Honorario
- Temporario
- Vitalicio
- Fallecido
- Cesante
- Renunciado

Notas
-----

- ``phone``, ``email``, ``mobile``, ``street``, ``city``, ``zip``, ``state_id`` y ``country_id`` se reutilizan desde Odoo estándar.
- ``tipo_registro`` se usa para mostrar u ocultar los bloques específicos de socios.
- ``email_aux`` y ``codigo`` tienen validación de formato y unicidad funcional.

from odoo import api, models


class SkySociosDemoGenerator(models.AbstractModel):
    _name = "sky.socios.demo.generator"
    _description = "Generador de datos demo para Sky Socios"

    def _get_ref(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

    def _set_xmlid(self, name, record):
        imd = self.env["ir.model.data"].sudo()
        existing = imd.search([("module", "=", "sky_socios"), ("name", "=", name)], limit=1)
        vals = {
            "module": "sky_socios",
            "name": name,
            "model": record._name,
            "res_id": record.id,
            "noupdate": False,
        }
        if existing:
            existing.write(vals)
        else:
            imd.create(vals)

    def _upsert_xmlid(self, name, model_name, values, search_domain=None):
        record = self._get_ref("sky_socios.%s" % name)
        if not record and search_domain:
            record = self.env[model_name].search(search_domain, limit=1)
        if record:
            record.write(values)
        else:
            record = self.env[model_name].create(values)
        self._set_xmlid(name, record)
        return record

    def _category(self, name):
        return self.env["sky.socio.categoria"].search([("name", "=", name)], limit=1).id

    def _country_ar(self):
        country = self.env.ref("base.ar", raise_if_not_found=False)
        return country.id if country else False

    def _family_values(self):
        return [
            (
                "sky_demo_familia_alvarez",
                {
                    "name": "Familia Alvarez",
                    "notas": "Familia completa para probar vista kanban y arbol familiar.",
                },
            ),
            (
                "sky_demo_familia_medina",
                {
                    "name": "Familia Medina",
                    "notas": "Incluye hijo mayor para probar pase manual a Activo.",
                },
            ),
            (
                "sky_demo_familia_paredes",
                {
                    "name": "Familia Paredes",
                    "notas": "Incluye cadetes de distintas edades para probar recategorizacion.",
                },
            ),
        ]

    def _partner_values(self, families):
        ar_id = self._country_ar()
        cat = self._category
        return [
            (
                "sky_demo_socio_alvarez_martin",
                {
                    "tipo_registro": "socio",
                    "apellido": "Alvarez",
                    "nombre": "Martin",
                    "genero": "m",
                    "fecha_nacimiento": "1978-04-12",
                    "estado_civil": "casado",
                    "activa": True,
                    "codigo": "SKY-0001",
                    "categoria_socio_id": cat("Activo"),
                    "grupo_familiar": "jefe",
                    "familia_id": families["sky_demo_familia_alvarez"].id,
                    "fecha_ingreso": "2001-03-15",
                    "fecha_pase": "1985-01-10",
                    "pais_residencia_id": ar_id,
                    "phone": "+54 11 4000-1001",
                    "phone_aux": "+54 9 11 5000-1001",
                    "email": "martin.alvarez@example.com",
                    "email_aux": "malvarez.demo@example.com",
                    "street": "Av. Demo 123",
                    "city": "Buenos Aires",
                    "zip": "1001",
                },
            ),
            (
                "sky_demo_socio_alvarez_clara",
                {
                    "tipo_registro": "socio",
                    "apellido": "Alvarez",
                    "nombre": "Clara",
                    "genero": "f",
                    "fecha_nacimiento": "1980-09-28",
                    "estado_civil": "casado",
                    "activa": True,
                    "codigo": "SKY-0002",
                    "categoria_socio_id": cat("Activo"),
                    "grupo_familiar": "conyuge",
                    "familia_id": families["sky_demo_familia_alvarez"].id,
                    "fecha_ingreso": "2004-07-01",
                    "fecha_pase": "2004-07-01",
                    "pais_residencia_id": ar_id,
                    "phone": "+54 11 4000-1002",
                    "email": "clara.alvarez@example.com",
                },
            ),
            (
                "sky_demo_socio_alvarez_lucia",
                {
                    "tipo_registro": "socio",
                    "apellido": "Alvarez",
                    "nombre": "Lucia",
                    "genero": "f",
                    "fecha_nacimiento": "2008-11-03",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0003",
                    "categoria_socio_id": cat("Cadete6"),
                    "grupo_familiar": "hijo",
                    "familia_id": families["sky_demo_familia_alvarez"].id,
                    "fecha_ingreso": "2012-02-01",
                    "pais_residencia_id": ar_id,
                    "email_aux": "lucia.alvarez@example.com",
                },
            ),
            (
                "sky_demo_socio_alvarez_tomas",
                {
                    "tipo_registro": "socio",
                    "apellido": "Alvarez",
                    "nombre": "Tomas",
                    "genero": "m",
                    "fecha_nacimiento": "2016-06-21",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0004",
                    "categoria_socio_id": cat("Cadete4"),
                    "grupo_familiar": "hijo",
                    "familia_id": families["sky_demo_familia_alvarez"].id,
                    "fecha_ingreso": "2018-01-15",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_medina_jorge",
                {
                    "tipo_registro": "socio",
                    "apellido": "Medina",
                    "nombre": "Jorge",
                    "genero": "m",
                    "fecha_nacimiento": "1969-02-05",
                    "estado_civil": "casado",
                    "activa": True,
                    "codigo": "SKY-0010",
                    "categoria_socio_id": cat("Activo"),
                    "grupo_familiar": "jefe",
                    "familia_id": families["sky_demo_familia_medina"].id,
                    "fecha_ingreso": "1996-05-20",
                    "fecha_pase": "1996-05-20",
                    "pais_residencia_id": ar_id,
                    "email": "jorge.medina@example.com",
                },
            ),
            (
                "sky_demo_socio_medina_paula",
                {
                    "tipo_registro": "socio",
                    "apellido": "Medina",
                    "nombre": "Paula",
                    "genero": "f",
                    "fecha_nacimiento": "1971-08-14",
                    "estado_civil": "casado",
                    "activa": True,
                    "codigo": "SKY-0011",
                    "categoria_socio_id": cat("Activo"),
                    "grupo_familiar": "conyuge",
                    "familia_id": families["sky_demo_familia_medina"].id,
                    "fecha_ingreso": "1998-02-10",
                    "fecha_pase": "1998-02-10",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_medina_nicolas",
                {
                    "tipo_registro": "socio",
                    "apellido": "Medina",
                    "nombre": "Nicolas",
                    "genero": "m",
                    "fecha_nacimiento": "2003-12-19",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0012",
                    "categoria_socio_id": cat("Juvenil"),
                    "grupo_familiar": "hijo",
                    "familia_id": families["sky_demo_familia_medina"].id,
                    "fecha_ingreso": "2007-04-01",
                    "pais_residencia_id": ar_id,
                    "email_aux": "nicolas.medina@example.com",
                },
            ),
            (
                "sky_demo_socio_paredes_sofia",
                {
                    "tipo_registro": "socio",
                    "apellido": "Paredes",
                    "nombre": "Sofia",
                    "genero": "f",
                    "fecha_nacimiento": "1984-03-30",
                    "estado_civil": "union",
                    "activa": True,
                    "codigo": "SKY-0020",
                    "categoria_socio_id": cat("Activo"),
                    "grupo_familiar": "jefe",
                    "familia_id": families["sky_demo_familia_paredes"].id,
                    "fecha_ingreso": "2010-09-01",
                    "fecha_pase": "2010-09-01",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_paredes_ines",
                {
                    "tipo_registro": "socio",
                    "apellido": "Paredes",
                    "nombre": "Ines",
                    "genero": "f",
                    "fecha_nacimiento": "2012-01-18",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0021",
                    "categoria_socio_id": cat("Cadete5"),
                    "grupo_familiar": "hijo",
                    "familia_id": families["sky_demo_familia_paredes"].id,
                    "fecha_ingreso": "2015-03-10",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_paredes_mateo",
                {
                    "tipo_registro": "socio",
                    "apellido": "Paredes",
                    "nombre": "Mateo",
                    "genero": "m",
                    "fecha_nacimiento": "2019-10-02",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0022",
                    "categoria_socio_id": cat("Cadete2"),
                    "grupo_familiar": "hijo",
                    "familia_id": families["sky_demo_familia_paredes"].id,
                    "fecha_ingreso": "2021-01-10",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_gomez_elena",
                {
                    "tipo_registro": "socio",
                    "apellido": "Gomez",
                    "nombre": "Elena",
                    "genero": "f",
                    "fecha_nacimiento": "1949-07-07",
                    "estado_civil": "viudo",
                    "activa": True,
                    "codigo": "SKY-0030",
                    "categoria_socio_id": cat("Activo"),
                    "grupo_familiar": "individual",
                    "familia_id": False,
                    "fecha_ingreso": "1978-04-01",
                    "fecha_pase": "1979-06-15",
                    "pais_residencia_id": ar_id,
                    "email": "elena.gomez@example.com",
                },
            ),
            (
                "sky_demo_socio_rossi_ana",
                {
                    "tipo_registro": "socio",
                    "apellido": "Rossi",
                    "nombre": "Ana",
                    "genero": "f",
                    "fecha_nacimiento": "1951-05-11",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0031",
                    "categoria_socio_id": cat("Vitalicio"),
                    "grupo_familiar": "individual",
                    "familia_id": False,
                    "fecha_ingreso": "1980-08-08",
                    "fecha_pase": "1981-01-01",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_sosa_lautaro",
                {
                    "tipo_registro": "socio",
                    "apellido": "Sosa",
                    "nombre": "Lautaro",
                    "genero": "m",
                    "fecha_nacimiento": "2009-09-09",
                    "estado_civil": "soltero",
                    "activa": True,
                    "codigo": "SKY-0032",
                    "categoria_socio_id": cat("Cadete6"),
                    "grupo_familiar": "individual",
                    "familia_id": False,
                    "fecha_ingreso": "2023-01-10",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_socio_torres_mario",
                {
                    "tipo_registro": "socio",
                    "apellido": "Torres",
                    "nombre": "Mario",
                    "genero": "m",
                    "fecha_nacimiento": "1962-02-22",
                    "estado_civil": "divorciado",
                    "activa": False,
                    "codigo": "SKY-0033",
                    "categoria_socio_id": cat("Renunciado"),
                    "grupo_familiar": "individual",
                    "familia_id": False,
                    "fecha_ingreso": "1995-01-01",
                    "fecha_renuncia": "2025-12-15",
                    "pais_residencia_id": ar_id,
                },
            ),
            (
                "sky_demo_contacto_proveedor",
                {
                    "name": "Proveedor Demo Club",
                    "tipo_registro": "otra_cuenta",
                    "email": "proveedor.demo@example.com",
                    "phone": "+54 11 4000-1099",
                    "street": "Calle Servicio 900",
                    "city": "Buenos Aires",
                },
            ),
        ]

    @api.model
    def _cron_generate_demo_data(self):
        families = {}
        for xmlid_name, values in self._family_values():
            families[xmlid_name] = self._upsert_xmlid(
                xmlid_name,
                "sky.familia",
                values,
                [("name", "=", values["name"])],
            )

        partners = {}
        for xmlid_name, values in self._partner_values(families):
            search_domain = [("codigo", "=", values["codigo"])] if values.get("codigo") else [("name", "=", values["name"])]
            partners[xmlid_name] = self._upsert_xmlid(xmlid_name, "res.partner", values, search_domain)

        families["sky_demo_familia_alvarez"].write({"jefe_id": partners["sky_demo_socio_alvarez_martin"].id})
        families["sky_demo_familia_medina"].write({"jefe_id": partners["sky_demo_socio_medina_jorge"].id})
        families["sky_demo_familia_paredes"].write({"jefe_id": partners["sky_demo_socio_paredes_sofia"].id})

        return True

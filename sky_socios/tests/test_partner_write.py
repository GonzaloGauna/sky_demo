from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerWrite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.socio_a = Partner.create({"tipo_registro": "socio", "apellido": "Pérez", "nombre": "Ana"})
        cls.socio_b = Partner.create({"tipo_registro": "socio", "apellido": "Gómez", "nombre": "Luis"})
        cls.other = Partner.create({"name": "Proveedor X", "tipo_registro": "proveedor"})

    def test_write_multi_without_name_fields(self):
        partners = self.socio_a | self.socio_b | self.other
        partners.write({"comment": "masivo"})
        self.assertEqual(self.socio_a.name, "Pérez, Ana")
        self.assertEqual(self.socio_b.name, "Gómez, Luis")
        self.assertEqual(self.other.name, "Proveedor X")

    def test_write_multi_with_name_fields(self):
        (self.socio_a | self.socio_b).write({"nombre": "Eva"})
        self.assertEqual(self.socio_a.name, "Pérez, Eva")
        self.assertEqual(self.socio_b.name, "Gómez, Eva")

    def test_create_company_with_existing_companies(self):
        # Reproduce el error al crear una empresa: stock escribe sobre los partners de todas las empresas.
        company = self.env["res.company"].create({"name": "Empresa de prueba socios"})
        self.assertTrue(company.partner_id)

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, onWillStart, useState } from "@odoo/owl";

const placeholder = "/web/static/img/placeholder.png";

class SkyFamilyTree extends Component {
    static template = "sky_socios.FamilyTree";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.openPartner = this.openPartner.bind(this);
        this.state = useState({ loading: true, data: null });
        onWillStart(async () => {
            const familyId = this.props.action.params?.family_id || this.props.action.context?.active_id;
            this.state.data = await this.orm.call("sky.familia", "get_family_tree_data", [familyId]);
            this.state.loading = false;
        });
    }

    openPartner(partnerId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    imageSrc(node) {
        if (!node.has_image) {
            return placeholder;
        }
        return imageUrl("res.partner", node.id, "image_1920", {
            unique: node.write_date || node.id,
        });
    }

    categoryStyle(node) {
        const color = node.category ? node.category.color : 0;
        const palette = [
            "#94a3b8",
            "#2563eb",
            "#16a34a",
            "#f59e0b",
            "#ef4444",
            "#8b5cf6",
            "#0ea5e9",
            "#14b8a6",
            "#ec4899",
            "#84cc16",
            "#6b7280",
            "#d97706",
            "#7c3aed",
        ];
        return `background:${palette[color % palette.length]}`;
    }
}

registry.category("actions").add("sky_socios_family_tree", SkyFamilyTree);

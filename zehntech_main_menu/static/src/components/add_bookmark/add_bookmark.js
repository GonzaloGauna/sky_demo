// import { Component } from "@odoo/owl";
// import { DropdownItem } from "@web/core/dropdown/dropdown_item";
// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { rpc } from "@web/core/network/rpc";
// import { _t } from "@web/core/l10n/translation";

// export class addBookmark extends Component {
//     static template = "zehntech_main_menu.AddBookmark";
//     static components = { DropdownItem };
//     static props = {};

//     setup() {
//         this.action = useService("action");
//     }

//     addBookmark() {
//         rpc("/web/menu_bookmark/add", {
//             name: window.document.title,
//             url: window.location.href,
//         });
//     }
// }

// registry.category("cogMenu").add("add-bookmark", { Component: addBookmark }, { sequence: 1 });


import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class addBookmark extends Component {
    static template = "zehntech_main_menu.AddBookmark";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
    }

    async addBookmark() {
        const result = await rpc("/web/menu_bookmark/add", {
            name: window.document.title,
            url: window.location.href,
        });
        if (result && result.error) {
            this.notification.add(result.error, { type: "warning" });
        } else {
            this.notification.add(_t("Bookmark added!"), { type: "success" });
        }
    }
}

registry.category("cogMenu").add("add-bookmark", { Component: addBookmark }, { sequence: 1 });
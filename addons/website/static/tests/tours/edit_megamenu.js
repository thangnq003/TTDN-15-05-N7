odoo.define("website.tour.edit_megamenu", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

const toggleMegaMenu = (stepOptions) => Object.assign({}, {
    content: "Toggles the mega menu.",
    trigger: '#top_menu .nav-item a.o_mega_menu_toggle',
    run: function () {
        // If the mega menu is displayed inside the extra menu items, it should
        // already be displayed.
        if (!this.$anchor[0].closest('.o_extra_menu_items')) {
            this.$anchor.click();
        }
    },
}, stepOptions);

tour.register('edit_megamenu', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: '#top_menu .nav-item a',
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: '.o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        extra_trigger: '.o_web_editor_dialog:visible',
        trigger: '.modal-body a.js_add_menu[data-type="mega"]',
    },
    {
        content: "Write a label for the new menu item",
        extra_trigger: '.o_link_dialog',
        trigger: '.o_link_dialog #o_link_dialog_label_input',
        run: 'text Megaaaaa!'
    },
    {
        content: "Save the new menu item",
        trigger: '.modal-dialog .btn-primary span:contains("Save")',
        run: 'click',
    },
    {
        content: "Save the changes to the menu",
        trigger: '.modal-dialog .btn-primary span:contains("Save")',
        run: 'click',
    },
    // Edit a menu item
    wTourUtils.clickOnEdit(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: '#oe_snippets.o_loaded'}),
    toggleMegaMenu({extra_trigger: '#top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")'}),
    {
        content: "Select the last menu link of the first column",
        trigger: '.s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(6)', // 6th is the last one
    },
    {
        content: "Hit the delete button to remove the menu link",
        trigger: '.oe_overlay .oe_snippet_remove',
    },
    {
        content: "Check that the last menu link was deleted",
        trigger: '.s_mega_menu_odoo_menu .row > div:first-child .nav:not(:has(> :nth-child(6)))',
        run: () => null,
    },
    {
        content: "Clicks on the first title item.",
        trigger: '.o_mega_menu h4',
    },
    {
        content: "Press enter.",
        trigger: '.o_mega_menu h4',
        run: function (actions) {
            this.$anchor[0].dispatchEvent(new window.InputEvent('input', {bubbles: true, inputType: 'insertParagraph'}));
        },
    },
    {
        content: "The menu should still be visible. Edit a menu item.",
        trigger: '.o_mega_menu h4',
        run: 'text New Menu Item',
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'a[data-action=edit]'}),
    toggleMegaMenu(),
    {
        content: "The menu item should have been renamed.",
        trigger: '.o_mega_menu h4:contains("New Menu Item")',
        run: function () {}, // it's a check
    },
]);
tour.register('edit_megamenu_big_icons_subtitles', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: '#top_menu .nav-item a',
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: '.o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        extra_trigger: ".o_web_editor_dialog",
        trigger: '.modal-body a.js_add_menu[data-type="mega"]',
    },
    {
        content: "Write a label for the new menu item",
        trigger: '.o_link_dialog #o_link_dialog_label_input',
        run: 'text Megaaaaa2!',
    },
    {
        content: "Save the new menu item",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Save the changes to the menu",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Check for the new mega menu",
        trigger: '#top_menu:has(.nav-item a.o_mega_menu_toggle:contains("Megaaaaa2!"))',
        run: function () {}, // it's a check
    },
    // Edit a menu item
    wTourUtils.clickOnEdit(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: '#oe_snippets.o_loaded'}),
    toggleMegaMenu({extra_trigger: '#top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa2!")'}),
    {
        content: "Select the first menu link of the first column",
        trigger: '.s_mega_menu_odoo_menu .row > div:first-child .nav > :first-child',
    },
    wTourUtils.changeOption("MegaMenuLayout", "we-toggler"),
    {
        content: "Select Big Icons Subtitles mega menu",
        trigger: '[data-select-label="Big Icons Subtitles"]',
    },
    wTourUtils.clickOnExtraMenuItem({extra_trigger: '#oe_snippets.o_loaded'}),
    {
        content: "Select the h4 of first menu link of the first column",
        trigger: '.s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child .media-body > h4',
        run: function (actions) {
            // Clicking on the h4 element first time leads to the selection of
            // the entire a.nav-link, due to presence of `o_default_snippet_text` class
            // hence, specify the selection on the h4 element
            actions.click();
            const range = document.createRange();
            range.selectNodeContents(this.$anchor[0]);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        },
    },
    {
        content: "Convert it to Bold",
        trigger: '#oe_snippets #toolbar #bold',
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'a[data-action=edit]'}),
    toggleMegaMenu(),
    {
        content: "The menu item should only convert selected text to Bold.",
        trigger: '.s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child .media-body > :last-child:not(:has(strong))',
        run: function () {}, // it's a check
    },
]);
});

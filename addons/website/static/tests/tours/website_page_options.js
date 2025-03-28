/** @odoo-module **/

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register("website_page_options", {
    test: true,
    url: "/?enable_editor=1",
}, [
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    wTourUtils.changeOption('TopMenuVisibility', 'we-button[data-visibility="transparent"]'),
    // It's important to test saving right after changing that option only as
    // this is why this test was made in the first place: the page was not
    // marked as dirty when that option was the only one that was changed.
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is transparent",
        trigger: '#wrapwrap.o_header_overlay',
        run: () => null, // it's a check
    },
    wTourUtils.clickOnEdit(),
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('topMenuColor', 'we-select.o_we_so_color_palette'),
    wTourUtils.changeOption('topMenuColor', 'button[data-color="black-50"]'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is in black-50",
        trigger: 'header#top.bg-black-50',
        run: () => null, // it's a check
    },
    wTourUtils.clickOnEdit(),
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    wTourUtils.changeOption('TopMenuVisibility', 'we-button[data-visibility="hidden"]'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is hidden",
        trigger: '#wrapwrap:has(header#top.d-none.o_snippet_invisible)',
        run: () => null, // it's a check
    },
    wTourUtils.clickOnEdit(),
    {
        content: "Click on 'header' in the invisible elements list",
        extra_trigger: '#oe_snippets.o_loaded',
        trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
    },
    wTourUtils.clickOnSnippet({id: 'o_footer', name: 'Footer'}),
    wTourUtils.changeOption('HideFooter', 'we-button[data-name="hide_footer_page_opt"] we-checkbox'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the footer is hidden and the header is visible",
        trigger: '#wrapwrap:has(.o_footer.d-none.o_snippet_invisible)',
        extra_trigger: '#wrapwrap header#top:not(.d-none)',
        run: () => null, // it's a check
    },
]);

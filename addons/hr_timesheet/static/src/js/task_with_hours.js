/** @odoo-module alias=hr_timesheet.task_with_hours **/

import field_registry from 'web.field_registry';
import { FieldMany2One } from 'web.relational_fields';

const TaskWithHours = FieldMany2One.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.additionalContext.hr_timesheet_display_remaining_hours = true;
        // By default, we keep the no_quick_create value or we set to false.
        this.nodeOptions.no_quick_create = this.nodeOptions.no_quick_create || false;
    },
    /**
     * @override
     */
    _getDisplayNameWithoutHours: function (value) {
        return value && value.split('\u00A0')[0];
    },
    /**
     * @override
     * @private
     */
    _onInputClick: function () {
        const context = Object.assign(
            this.record.getContext(this.recordParams),
            this.additionalContext
        );
        // We don't want to quick create if no project is set in the timesheet
        this.nodeOptions.no_quick_create =
            this.nodeOptions.no_quick_create || (!('default_project_id' in context) || !context.default_project_id);
        this._super.apply(this, arguments);
    },
    /**
     * @override
     * @private
     */
    _renderEdit: function (){
        this.m2o_value = this._getDisplayNameWithoutHours(this.m2o_value);
        this._super.apply(this, arguments);
    },
});

field_registry.add('task_with_hours', TaskWithHours);

export default TaskWithHours;

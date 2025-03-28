/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';
import { insert, unlinkAll } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Notification extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('failure_type' in data) {
                data2.failure_type = data.failure_type;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('notification_status' in data) {
                data2.notification_status = data.notification_status;
            }
            if ('notification_type' in data) {
                data2.notification_type = data.notification_type;
            }
            if ('res_partner_id' in data) {
                if (!data.res_partner_id) {
                    data2.partner = unlinkAll();
                } else {
                    data2.partner = insert({
                        display_name: data.res_partner_id[1],
                        id: data.res_partner_id[0],
                    });
                }
            }
            return data2;
        }

    }

    Notification.fields = {
        failure_type: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
        message: many2one('mail.message', {
            inverse: 'notifications',
        }),
        notification_status: attr(),
        notification_type: attr(),
        partner: many2one('mail.partner'),
    };
    Notification.identifyingFields = ['id'];
    Notification.modelName = 'mail.notification';

    return Notification;
}

registerNewModel('mail.notification', factory);

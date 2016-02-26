/**
 * Created by mmalkov on 29.01.16.
 */

angular.module('nVesta', ['ngRoute', 'hitsl.core'])
.config(['$routeProvider', '$locationProvider', function ($routeProvider, $locationProvider) {
    //$locationProvider.html5Mode(true);
    $routeProvider
        .when('/', {
            templateUrl: '/admin/static/partials/index.html',
            controller: 'IndexController'
        })
        .when('/add', {
            templateUrl: '/admin/static/partials/edit-meta.html',
            controller: 'EditRbMetaController'
        })
        .when('/edit/:rb_code/meta', {
            templateUrl: '/admin/static/partials/edit-meta.html',
            controller: 'EditRbMetaController'
        })
        .when('/edit/:rb_code/data', {
            templateUrl: '/admin/static/partials/edit-data.html',
            controller: 'EditRbDataController'
        })
        .when('/import', {
            templateUrl: '/admin/static/partials/import.html',
            controller: 'ImportController'
        })
        .otherwise({
            redirectTo: '/'
        });
}])
.constant('Config', {
    api: {
        rb: {
            list: '/api/v2/rb/',
            create: '/api/v2/rb/',
            //update: '/api/v2/rb/{0}/',
            meta: {
                view: '/api/v2/rb/{0}/meta/',
                update: '/api/v2/rb/{0}/meta/'
            },
            data: {
                list: '/api/v2/rb/{0}/data/',
                create: '/api/v2/rb/{0}/data/',
                update: '/api/v2/rb/{0}/data/id/{1}/',
                remove: '/api/v2/rb/{0}/data/id/{1}/',
                view: '/api/v2/rb/{0}/data/{1}/'
            },
            fix: '/api/v2/rb/{0}/fix/'
        },
        imp: {
            nsi: {
                list: '/api/integrations/nsi/list/',
                import: '/api/integrations/nsi/import/',
                utils: {
                    kladr: '/api/integrations/nsi/utils/kladr/'
                }
            }
        }
    }
})
.service('IntegrationsApi', ['ApiCalls', 'Config', function (ApiCalls, Config) {
    this.nsi_list = function () {
        return ApiCalls.wrapper('GET', Config.api.imp.nsi.list);
    };
    this.nsi_import = function (data) {
        return ApiCalls.wrapper('POST', Config.api.imp.nsi.import, undefined, data);
    };
    this.nsi_update_kladr = function () {
        return ApiCalls.wrapper('POST', Config.api.imp.nsi.utils.kladr);
    }
}])
.service('RefBookApi', ['ApiCalls', 'Config', function (ApiCalls, Config) {
    this.rb_list = function () {
        return ApiCalls.wrapper('GET', Config.api.rb.list)
    };
    this.rb_create = function (data) {
        return ApiCalls.wrapper('POST', Config.api.rb.create, undefined, data)
    };
    this.rb_meta_view = function (rb_code) {
        return ApiCalls.wrapper('GET', Config.api.rb.meta.view.format(rb_code))
    };
    this.rb_meta_edit = function (data, rb_code) {
        return ApiCalls.wrapper('PUT', Config.api.rb.meta.update.format(rb_code || data.code), undefined, data)
    };
    this.rb_data_list = function (rb_code) {
        return ApiCalls.wrapper('GET', Config.api.rb.data.list.format(rb_code))
    };
    this.rb_data_create = function (data, rb_code) {
        return ApiCalls.wrapper('POST', Config.api.rb.data.create.format(rb_code), undefined, data)
    };
    this.rb_data_update = function (data, rb_code, record_id) {
        return ApiCalls.wrapper('PUT', Config.api.rb.data.update.format(rb_code, record_id || data._id), undefined, data)
    };
    this.rb_data_remove = function (rb_code, record_id) {
        return ApiCalls.wrapper('DELETE', Config.api.rb.data.remove.format(rb_code, record_id))
    };
    this.rb_data_view = function (rb_code, record_id) {
        return ApiCalls.wrapper('GET', Config.api.rb.data.view.format(rb_code, record_id))
    };
}])
.service('RefBookRegistry', ['RefBookApi', 'RefBookApi', function (RefBookApi) {
    var self = this;
    var rb_list = this.rb_list = [];
    this.reload = function () {
        RefBookApi.rb_list().then(function (result) {
            _.replace_array(rb_list, result);
        })
    };
    this.get = function (rb_code) {
        for (var i = 0; i < rb_list.length; i++) {
            if (rb_list[i].code == rb_code) {
                return rb_list[i];
            }
        }
    }
}])
.controller('IndexController', ['$scope', 'RefBookRegistry', function ($scope, RefBookRegistry) {
    $scope.rb_list = RefBookRegistry.rb_list;
    RefBookRegistry.reload();
}])
.controller('EditRbMetaController', [
    '$scope', '$routeParams', '$location', 'RefBookApi', 'RefBookRegistry', 'NotificationService',
    function ($scope, $routeParams, $location, RefBookApi, RefBookRegistry, NotificationService) {
    $scope.rb_list = RefBookRegistry.rb_list;
    $scope.meta = {};
    $scope.rb_code = $routeParams.rb_code;
    var on_load = function (rb_meta) {
        var primary_link = {},
            fields = _.map(rb_meta.fields, function (field) {
            if (!!field.link) {
                var code = _.safe_traverse(field, ['link', 'code']);
                if (code) {
                    var ref_book = RefBookRegistry.get(code);
                    var linked_field_obj = _.find(ref_book.fields, {key: field.link.linked_field});
                    _.extend(field.link, {
                        refbook: ref_book,
                        linked_field_obj: linked_field_obj
                    })

                }
            }
            return _.extend(field, {
                allow_link: !! field.link
            });
        });
        if (!!rb_meta.primary_link) {
            var refbook = RefBookRegistry.get(rb_meta.primary_link.right_rb);
            angular.extend(primary_link, {
                refbook: refbook,
                left: _.find(fields, function (field) { return field.key == rb_meta.primary_link.left_field }),
                right: _.find(refbook.fields, function (field) { return field.key == rb_meta.primary_link.right_field })
            })
        }
        angular.extend($scope.meta, rb_meta, {
            fields: fields,
            primary_link: primary_link
        });
        return rb_meta
    };
    var on_finish = function (result) {
        $location.url('/edit/{0}/meta'.format(result.code));
        NotificationService.notify(200, 'Структура успешно сохранена', 'success', 10000);
        RefBookRegistry.reload();
        return result;
    };
    var prepare_meta = function () {
        var meta = $scope.meta;
        return {
            _id: meta._id,
            code: meta.code,
            name: meta.name,
            oid: meta.oid,
            description: meta.description,
            primary_link: (meta.primary_link.left && meta.primary_link.right && meta.primary_link.refbook)?{
                left_field: meta.primary_link.left.key,
                right_field: meta.primary_link.right.key,
                right_rb: meta.primary_link.refbook.code
            }:null,
            version: meta.version,
            fields: _.map(
                meta.fields,
                function (field) {
                    return {
                        key: field.key,
                        name: field.name,
                        link: (field.allow_link)?(process_link(field.link)):(null)
                    };
                }
            )
        }
    };
    var process_link = function (link) {
        return {
            key: link.key,
            code: link.refbook.code,
            linked_field: link.linked_field_obj.key,
            list: link.list
        }
    };
    RefBookRegistry.reload();
    if (!_.isUndefined($scope.rb_code)) {
        RefBookApi.rb_meta_view($routeParams.rb_code).then(on_load)
    } else {
        angular.extend($scope.meta, {
            code: '',
            name: '',
            oid: '',
            description: '',
            version: 0,
            fields: [],
            primary_link: {}
        })
    }
    $scope.save = function () {
        var meta = prepare_meta();
        if ($scope.meta._id) {
            RefBookApi.rb_meta_edit(meta, $routeParams.rb_code).then(on_finish)
        } else {
            RefBookApi.rb_create(meta).then(on_finish)
        }
    };
    $scope.add_field = function () {
        $scope.meta.fields.push({
            key: '',
            name: '',
            link: {
                refbook: {},
                key: '',
                code: null,
                linked_field: '',
                list: false
            },
            is_new: true,
            allow_link: false
        })
    };
}])
.controller('EditRbDataController', [
    '$scope', '$routeParams', '$location', 'RefBookApi', 'NotificationService',
    function ($scope, $routeParams, $location, RefBookApi, NotificationService) {
    var meta = $scope.meta = {};
    var rb_code = $scope.rb_code = $routeParams.rb_code;
    var data = $scope.data = [];

    RefBookApi.rb_meta_view(rb_code).then(function (rb_meta) {
        $scope.meta = rb_meta;
    });

    RefBookApi.rb_data_list(rb_code).then(function (rb_data) {
        _.replace_array(data, rb_data);
    });

    $scope.addRow = function () {
        var new_record = {};
        _.map(meta.fields, function (field) {
            new_record[field.key] = '';
        });
        data.push({
            $edit: new_record
        });
    };
    $scope.editRecord = function (record) {
        record.$edit = angular.copy(record);
    };
    $scope.cancelRecord = function (record) {
        record.$edit = undefined;
        if (!record._id) {
            _.replace_array(data, _.without(data, record))
        }
    };
    var after_save_record_factory = function (record) {
        return function (result) {
            angular.extend(record, result);
            record.$edit = undefined;
            NotificationService.notify(200, 'Запись сохранена', 'success', 10000);
            return result;
        }
    };
    $scope.saveRecord = function (record) {
        if (!record._id) {
            RefBookApi.rb_data_create(record.$edit, rb_code).then(after_save_record_factory(record))
        } else {
            RefBookApi.rb_data_update(record.$edit, rb_code, record._id).then(after_save_record_factory(record));
        }
    };
    $scope.deleteRecord = function (record) {
        if (!record._id) {
            _.replace_array(data, _.without(data, record))
        } else {
            console.log('Не имплементировано пока');
            // RefBookApi.rb_data_remove(rb_code, record._id).then(function (result) {})
        }
    }
}])
.controller('ImportController', [
    '$scope', '$routeParams', 'IntegrationsApi', 'NotificationService',
    function ($scope, $routeParams, IntegrationsApi, NotificationService) {
        $scope.code = null;
        $scope.list = null;

        var update = function () {
            $scope.code = true;
            return IntegrationsApi.nsi_list().then(function (result) {
                $scope.list = result;
                $scope.code = null;
                return result;
            });
        };
        update();

        var nsi_import = function (data) {
            $scope.code = data.code;
            return IntegrationsApi.nsi_import(data).then(
                function (result) {
                    $scope.code = null;
                    NotificationService.notify(200, 'Загрузка справочникa {0} ({1}) из НСИ завершена'.format(data.name, data.code));
                    return result;
                },
                function (result) {
                    $scope.code = null;
                    return result;
                }
            )
        };

        $scope.nsi_import = function (data) {
            nsi_import(data).then(update, update);
        };

        $scope.nsi_import_all = function () {
            var required = _.filter($scope.list, function (item) {
                return _.safe_traverse(item, ['our', 'version']) != item.their.version && ! ['KLD172', 'STR172'].has(item.their.code);
            });
            function import_next() {
                var data = required.shift();
                if (data) {
                    nsi_import(data.their).then(import_next)
                } else {
                    update().then(function () {
                        NotificationService.notify(200, 'Загрузка всех справочников завершена', 'success');
                    });
                }
            }
            import_next();
        };
    }
])
;
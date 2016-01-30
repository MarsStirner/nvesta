/**
 * Created by mmalkov on 10.06.15.
 */
'use strict';
angular.module('hitsl.core')
.config([
    '$interpolateProvider',
    function ($interpolateProvider) {
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
    }])
.factory('TimeoutCallback', ['$timeout', '$interval', function ($timeout, $interval) {
    var Timeout = function (callback, timeout) {
        this.timeout = timeout;
        this.hideki = null;
        this.interval_promise = null;
        this.callback = callback;
    };
    Timeout.prototype.kill = function () {
        if (this.hideki) {
            $timeout.cancel(this.hideki);
            this.hideki = null;
        }
        if (this.interval_promise) {
            $interval.cancel(this.interval_promise);
            this.interval_promise = null;
        }
        return this;
    };
    Timeout.prototype.start = function (timeout) {
        this.kill();
        if (timeout !== undefined) {
            this.timeout = timeout;
        }
        this.hideki = $timeout(this.callback, this.timeout);
        return this;
    };
    Timeout.prototype.start_interval = function (count, timeout) {
        this.kill();
        if (timeout !== undefined) {
            this.timeout = timeout;
        }
        this.interval_promise = $interval(this.callback, this.timeout, count || 0, false);
        return this;
    };
    return Timeout;
}])

;

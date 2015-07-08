;(function (define) {
    'use strict';
    define([
        'teams/js/views/team_card',
        'common/js/components/views/paginated_view'
    ], function (TeamCardView, PaginatedView) {
        var TeamsView = PaginatedView.extend({
            type: 'teams',
            cardView: TeamCardView
        });
        return TeamsView;
    });
}).call(this, define || RequireJS.define);

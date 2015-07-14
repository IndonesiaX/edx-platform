;(function (define) {
    'use strict';

    define(['backbone',
            'underscore',
            'gettext',
            'js/components/header/views/header',
            'js/components/header/models/header',
            'js/components/tabbed/views/tabbed_view',
            'teams/js/views/topics',
            'teams/js/collections/topic',
            'teams/js/views/teams',
            'teams/js/collections/team',
            'text!teams/templates/teams_tab.underscore'],
           function (Backbone, _, gettext, HeaderView, HeaderModel, TabbedView,
                     TopicsView, TopicCollection, TeamsView, TeamCollection, teamsTemplate) {
               var TeamTabView = Backbone.View.extend({
                   initialize: function(options) {
                       var router, TempTabView, self = this;
                       this.course_id = options.course_id;
                       this.topics = options.topics;
                       this.teams_url = options.teams_url;
                       router = new (Backbone.Router.extend({
                           routes: {
                               'topics/:topic_id': _.bind(self.goToTopic, self),
                               ':tab': _.bind(self.goToTab, self)
                           }
                       }))();
                       this.headerModel = new HeaderModel({
                           description: gettext("Course teams are organized into topics created by course instructors. Try to join others in an existing team before you decide to create a new team!"),
                           title: gettext("Teams")
                       });
                       this.headerView = new HeaderView({
                           model: this.headerModel
                       });
                       // TODO replace this with actual views!
                       TempTabView = Backbone.View.extend({
                           initialize: function (options) {
                               this.text = options.text;
                           },

                           render: function () {
                               this.$el.text(this.text);
                           }
                       });
                       this.mainView = this.tabbedView = new TabbedView({
                           tabs: [{
                               title: gettext('My Teams'),
                               url: 'teams',
                               view: new TempTabView({text: 'This is the new Teams tab.'})
                           }, {
                               title: gettext('Browse'),
                               url: 'browse',
                               view: new TopicsView({
                                   collection: new TopicCollection(
                                       this.topics,
                                       {url: options.topics_url, course_id: this.course_id, parse: true}
                                   ).bootstrap(),
                                   router: router
                               })
                           }],
                           router: router
                       });
                   },

                   render: function() {
                       this.$el.html(_.template(teamsTemplate));
                       this.headerView.setElement(this.$('.teams-header')).render();
                       this.mainView.setElement(this.$('.teams-main')).render();
                       return this;
                   },

                   /**
                    * Render the list of teams for the given topic ID.
                    */
                   goToTopic: function (topicID) {
                       // Lazily load the teams-for-topic view in
                       // order to avoid making an extra AJAX call.
                       if (this.teamsView === undefined || this.teamsView.topic_id !== topicID) {
                           var teamCollection = new TeamCollection([], {
                               course_id: this.course_id,
                               url: this.teams_url,
                               topic_id: topicID,
                               per_page: 5 // TODO determine the right number
                           }).bootstrap();
                           teamCollection.goTo(1);
                           this.teamsView = new TeamsView({collection: teamCollection});
                       }
                       this.mainView = this.teamsView;
                       this.render();
                    },

                   /**
                    * Set up the tabbed view and switch tabs.
                    */
                   goToTab: function (tab) {
                       this.mainView = this.tabbedView;
                       // Note that `render` should be called first so
                       // that the tabbed view's element is set
                       // correctly.
                       this.render();
                       this.tabbedView.setActiveTab(tab);
                   }
               });

               return TeamTabView;
           });
}).call(this, define || RequireJS.define);

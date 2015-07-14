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
               var ViewWithHeader = Backbone.View.extend({
                   initialize: function (options) {
                       this.header = options.header;
                       this.main = options.main;
                   },

                   render: function () {
                       this.$el.html(_.template(teamsTemplate));
                       this.header.setElement(this.$('.teams-header')).render();
                       this.main.setElement(this.$('.teams-main')).render();
                       return this;
                   }
               });

               var TeamTabView = Backbone.View.extend({
                   initialize: function(options) {
                       var TempTabView, self = this;
                       this.course_id = options.course_id;
                       this.topics = options.topics;
                       this.teams_url = options.teams_url;
                       this.router = new (Backbone.Router.extend({
                           routes: {
                               'topics/:topic_id': _.bind(self.goToTopic, self),
                               ':tab': _.bind(self.goToTab, self)
                           }
                       }))();
                       // TODO replace this with actual views!
                       TempTabView = Backbone.View.extend({
                           initialize: function (options) {
                               this.text = options.text;
                           },

                           render: function () {
                               this.$el.text(this.text);
                           }
                       });
                       this.topicsCollection = new TopicCollection(
                           this.topics,
                           {url: options.topics_url, course_id: this.course_id, parse: true}
                       ).bootstrap();
                       this.mainView = this.tabbedView = new ViewWithHeader({
                           header: new HeaderView({
                               model: new HeaderModel({
                                   description: gettext("Course teams are organized into topics created by course instructors. Try to join others in an existing team before you decide to create a new team!"),
                                   title: gettext("Teams")
                               })
                           }),
                           main: new TabbedView({
                               tabs: [{
                                   title: gettext('My Teams'),
                                   url: 'teams',
                                   view: new TempTabView({text: 'This is the new Teams tab.'})
                               }, {
                                   title: gettext('Browse'),
                                   url: 'browse',
                                   view: new TopicsView({
                                       collection: this.topicsCollection,
                                       router: this.router
                                   })
                               }],
                               router: this.router
                           })
                       });
                   },

                   render: function() {
                       this.mainView.setElement(this.$el).render();
                       return this;
                   },

                   /**
                    * Render the list of teams for the given topic ID.
                    */
                   goToTopic: function (topicID) {
                       // Lazily load the teams-for-topic view in
                       // order to avoid making an extra AJAX call.
                       if (this.teamsView === undefined ||
                           this.teamsView.main.collection.topic_id !== topicID) {
                           var teamCollection = new TeamCollection([], {
                               course_id: this.course_id,
                               url: this.teams_url,
                               topic_id: topicID,
                               per_page: 5 // TODO determine the right number
                           }).bootstrap(),
                               topic = this.topicsCollection.findWhere({'id': topicID}),
                               headerView = new HeaderView({
                                   model: new HeaderModel({
                                       description: _.escape(
                                           interpolate(
                                               gettext('Teams working on projects relating to %(topic)s'),
                                               {topic: topic.get('name')},
                                               true
                                           )
                                       ),
                                       title: _.escape(topic.get('name')),
                                       breadcrumbs: [{
                                           title: 'All topics',
                                           url: '#'
                                       }]
                                   }),
                                   events: {
                                       'click nav.breadcrumbs a.nav-item': function (event) {
                                           event.preventDefault();
                                           self.router.navigate('browse', {trigger: true});
                                       }
                                   }
                               }),
                               self = this;
                           teamCollection.goTo(1);
                           this.teamsView = new ViewWithHeader({
                               header: headerView,
                               main: new TeamsView({collection: teamCollection})
                           });
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
                       this.tabbedView.main.setActiveTab(tab);
                   }
               });

               return TeamTabView;
           });
}).call(this, define || RequireJS.define);

(function(){
  'use strict';

  var website = openerp.website;
  website.snippet.animationRegistry.brandDropdown = website.snippet.Animation.extend({
    selector : "#brandDropDown",
    start: function(){
      this.redrow();
    },
    stop: function(){
      this.clean();
    },

    redrow: function(debug){
      this.clean(debug);
      this.build(debug);
    },

    clean:function(debug){
      this.$target.empty();
    },

    build: function(debug){
      var self     = this,
      selector_drop = $("#brandDropDown"),
      $active_li = $('.brand a');
      selector_drop.html($active_li.html()+ '<span class="caret"></span>');

    },

  })

})();

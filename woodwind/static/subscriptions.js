$(function() {

    $(".feed-details").css({display: "none"});

    $(".show-details").click(function(evt) {
        evt.preventDefault();
        var target = $(this).data("target");
        $("#" + target).css({display: "inherit"});
        $(this).css({display: "none"});
    });

    $("form.edit-subscription").submit(function(evt) {
        var form = $(this);
        evt.preventDefault();
        $(".save-status", form).html("Saving&hellip;");
        $.post(form.attr('action'), form.serialize(), function success(){
            $(".save-status", form).html("Saved.");
        }).fail(function failure() {
            $(".save-status", form).html("Save Failed!");
        });
    });

    $("form.poll-now").submit(function(evt) {
        var form = $(this);
        evt.preventDefault();

        $(".poll-status", form).html("");
        
        $.post(form.attr('action'), form.serialize(), function success(){
            $(".poll-status", form).html("Poll Requested.");
        }).fail(function failure() {
            $(".poll-status", form).html("Polling Failed!");
        });
        
    });

});

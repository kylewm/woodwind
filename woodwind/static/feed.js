$(function(){
    function clickOlderLink(evt) {
        evt.preventDefault();
        $.get(this.href, function(result) {
            $(".pager").replaceWith(
                $("article,.pager", $(result)));
            attachListeners();
        });
    }

    function clickShowReplyForm(evt) {
        var a = $(this);
        evt.preventDefault();
        $(".reply-form", a.parent()).css('display', 'inherit');
        a.css('display', 'none');
    }

    function submitMicropubForm(evt) {
        evt.preventDefault();

        var form = $(this);
        var endpoint = form.attr('action');
        var responseArea = $('.submit-response', form);

        $.post(
            '/_forward',
            '_url=' + encodeURIComponent(endpoint) + '&' + form.serialize(),
            function(result) {
                if (result.code == 200) {
                    responseArea.html('<a target="_blank" href="' + result.location + '">Success!</a>');
                } else {
                    responseArea.html('Failure');
                }
            },
            'json'
        );
        responseArea.html('Posting…');
    }

    function attachListeners() {
        $(".reply-form").css('display', 'none');
        $(".show-reply-form").css('display', 'inline');

        $("#older-link").off('click').click(clickOlderLink);
        $(".show-reply-form").off('click').click(clickShowReplyForm);

        $(".like-form, .reply-form").off('submit').submit(submitMicropubForm);
    }



    attachListeners();
});

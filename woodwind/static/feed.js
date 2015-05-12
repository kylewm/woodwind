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
        $(".like-form", a.parent()).hide();
        $(".reply-form", a.parent()).toggle();//css('display', 'inherit');
        //a.css('display', 'none');
    }

    function clickShowLikeForm(evt) {
        var a = $(this);
        evt.preventDefault();
        $(".reply-form", a.parent()).hide();
        $(".like-form", a.parent()).toggle();
        //a.css('display', 'none');
    }

    function submitMicropubForm(evt) {
        evt.preventDefault();

        var form = $(this).closest('form');
        var replyArea = form.parent();
        var endpoint = form.attr('action');
        var responseArea = $('.micropub-response', replyArea);
        var formData = form.serializeArray();
        formData.push({name: this.name, value: this.value});

        $.post(
            form.attr('action'),
            formData,
            function(result) {
                if (Math.floor(result.code / 100) == 2) {
                    responseArea.html('<a target="_blank" href="' + result.location + '">Success!</a>');
                    $(".micropub-form textarea").val("");
                } else {
                    responseArea.html('Failure');
                }
            },
            'json'
        );


        responseArea.html('Posting…');
    }

    function attachListeners() {
        $(".reply-form, .like-form").css('display', 'none');

        $("#older-link").off('click').click(clickOlderLink);
        $(".show-reply-form").off('click').click(clickShowReplyForm);
        $(".show-like-form").off('click').click(clickShowLikeForm);

        $(".micropub-form button[type='submit']").off('click').click(submitMicropubForm);

        $(".micropub-form .content").focus(function (){
            $(this).animate({ height: "4em" }, 200);
        });
    }


    function clickUnfoldLink(evt) {
        $('#fold').after($('#fold').children())
        $('#unfold-link').hide();
    }


    function foldNewEntries(entries) {
        $('#fold').prepend(entries.join('\n'));
        attachListeners();
        $('#unfold-link').text($('#fold').children().length + " New Posts");
        $('#unfold-link').off('click').click(clickUnfoldLink);
        $('#unfold-link').show();
    }

    // topic will be user:id or feed:id
    function webSocketSubscribe(topic) {
        if ('WebSocket' in window) {
            var ws = new WebSocket(window.location.origin
                                   .replace(/http:\/\//, 'ws://')
                                   .replace(/https:\/\//, 'wss://')
                                   + '/_updates');

            ws.onopen = function(event) {
                // send the topic
                console.log('subscribing to topic: ' + topic);
                ws.send(topic);
            };
            ws.onmessage = function(event) {
                console.log(event);
                var data = JSON.parse(event.data);
                foldNewEntries(data.entries);
            };
        }
    }

    attachListeners();
    if (WS_TOPIC) {
        webSocketSubscribe(WS_TOPIC);
    }
});

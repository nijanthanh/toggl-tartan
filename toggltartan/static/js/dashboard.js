//== Class definition
var Dashboard = function () {

    var calendarInit = function (api_token) {
        if ($('#m_calendar').length === 0) {
            return;
        }

        $('#m_calendar').fullCalendar({
            header: {
                left: 'prev,next today',
                center: 'title',
                right: 'month,agendaWeek,agendaDay,listWeek'
            },
            editable: false,
            eventLimit: true, // allow "more" link when too many events
            navLinks: true,
            events: '/event_data/' + api_token,
            eventRender: function (event, element) {
                if (element.hasClass('fc-day-grid-event')) {
                    element.data('content', event.description);
                    element.data('placement', 'top');
                    mApp.initPopover(element);
                } else if (element.hasClass('fc-time-grid-event')) {
                    element.find('.fc-title').append('<div class="fc-description">' + event.description + '</div>');
                } else if (element.find('.fc-list-item-title').lenght !== 0) {
                    element.find('.fc-list-item-title').append('<div class="fc-description">' + event.description + '</div>');
                }
            }
        });
    }

    var submitApiToken = function () {
        $('#api_token_form').validate({
            rules: {
                api_token: {
                    required: true,
                    rangelength: [32, 33]
                }
            },
            messages: {
                api_token: {
                    required: "Please copy the API token from your <a href='https://www.toggl.com/app/profile' target='_blank'>Toggl Profile Page</a>",
                    rangelength: "The Toggl API token should token should be 32 characters long"
                }
            },
            submitHandler: function (form) {
                mApp.block('#content', {
                    overlayColor: '#000000',
                    type: 'loader',
                    state: 'primary',
                    message: 'Processing...'
                });

                $('#file_upload_div').addClass("m--hide");
                $('#modify_calendar_alert').addClass("m--hide");
                $('#event_calendar').addClass("m--hide");
                $('#upload_file_help_text').addClass("m--hide");
                $('#alertDiv').addClass("m--hide");

                $.ajax({
                    type: 'POST',
                    url: "/submit_api_token",
                    data: {
                        'api_token': $("input[name=api_token]").val()
                    },
                    success: function (response) {


                        if (response.status == 'success') {
                            var api_token = $("input[name=api_token]").val();
                            $('#api_token_form').data('api_token', api_token);

                            $.getJSON('/event_data/' + api_token, function (data) {
                                mApp.unblock('#content');

                                if (!$.isArray(data) || !data.length) {
                                    // TODO Show DIV with message to upload file
                                    $('#file_upload_div').removeClass("m--hide");
                                } else {
                                    $('#modify_calendar_alert').removeClass("m--hide");
                                    calendarInit(api_token);
                                    $('#event_calendar').removeClass("m--hide");
                                    $('#upload_file_help_text').removeClass("m--hide");
                                }
                            });


                        } else {
                            mApp.unblock('#content');

                            $('#alertDiv').removeClass("m--hide");
                            $('#alertText').html(response.data);
                            $('#event_calendar').addClass("m--hide");
                            $('#file_upload_div').addClass("m--hide");
                            return;
                        }
                    },
                    error: function (response) {
                        mApp.unblock('#content');
                        $('#alertDiv').removeClass("m--hide");
                        $('#alertText').text("An unexpected error was encountered.");

                        $('#event_calendar').addClass("m--hide");
                        $('#file_upload_div').addClass("m--hide");

                        return;
                    },
                    dataType: 'json'
                });
            }

        });
    }

    var uploadCalendarFile = function () {
        /*$('#file_upload_form').validate({
            rules: {
                calendar_file_input: {
                    required: true
                }
            },
            messages: {
                calendar_file_input: {
                    required: "Please choose an ics file to upload. You can do this by exporting a calendar from either <a href='https://s3.andrew.cmu.edu/sio/#schedule-home' " +
                    " target='_blank'>SIO</a> or Google Calendar"
                }
            },
            submitHandler: function (form) { */
        /*
        $('#file_upload_form').submit(function(e) {
            e.preventDefault();
                mApp.block('#content', {
                    overlayColor: '#000000',
                    type: 'loader',
                    state: 'primary',
                    message: 'Processing...'
                });

                $('#alertFileDiv').addClass("m--hide");

                console.log($("#file_upload_form")[0])
                var fd = new FormData($("#file_upload_form")[0]);
                console.log(fd)

                $.ajax({
                    type: 'POST',
                    url: "/upload_calendar_file",
                    data: fd,
                    success: function (response) {
                        mApp.unblock('#content');

                        if (response.status == 'success') {
                            console.log("SUCCESS");

                        } else {
                            $('#alertFileDiv').removeClass("m--hide");
                            $('#alertFileText').html(response.data);
                            return;
                        }
                    },
                    error: function (response) {
                        mApp.unblock('#content');
                        $('#alertFileDiv').removeClass("m--hide");
                        $('#alertFileText').text("An unexpected error was encountered.");

                        return;
                    },
                    cache: false,
                    contentType: false,
                    processData: false
                    //dataType: 'json'
                });

        });
        */
    }

    return {
        init: function () {
            submitApiToken();
            uploadCalendarFile();
        }
    };
}();

//== Class initialization on page load
jQuery(document).ready(function () {
    Dashboard.init();

    $("#show_import_calendar_div").click(function () {
        $('#file_upload_div').removeClass("m--hide");
        $('#modify_calendar_alert').addClass("m--hide");
    })
});
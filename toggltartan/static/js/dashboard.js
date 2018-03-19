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
                mApp.block('#api_token_portlet', {
                    overlayColor: '#000000',
                    type: 'loader',
                    state: 'primary',
                    message: 'Processing...'
                });

                $.ajax({
                    type: 'POST',
                    url: "/submit_api_token",
                    data: {
                        'api_token': $("input[name=api_token]").val()
                    },
                    success: function (response) {
                        mApp.unblock('#api_token_portlet');

                        if (response.status == 'success') {
                            var api_token = $("input[name=api_token]").val();
                            $('#api_token_form').data('api_token', api_token);

                            $('#file_upload_form').removeClass("m--hide");

                            $.getJSON('/event_data/' + api_token, function (data) {
                                console.log(data);
                                if( !$.isArray(data) ||  !data.length ) {
                                  // Show DIV with message to upload file
                                } else {
                                    // Show div with message to upload file to replace
                                    calendarInit(api_token);
                                    $('#event_calendar').removeClass("m--hide");
                                }
                            });


                        } else {
                            $('#alertDiv').removeClass("m--hide");
                            $('#alertText').html(response.data);
                            $('#event_calendar').addClass("m--hide");
                            $('#file_upload_form').addClass("m--hide");
                            return;
                        }
                    },
                    error: function (response) {
                        mApp.unblock('#api_token_portlet');
                        $('#alertDiv').removeClass("m--hide");
                        $('#alertText').text("An unexpected error was encountered.");

                        $('#event_calendar').addClass("m--hide");
                        $('#file_upload_form').addClass("m--hide");

                        return;
                    },
                    dataType: 'json'
                });
            }

        });
    }

    return {
        init: function () {
            submitApiToken();
        }
    };
}();

//== Class initialization on page load
jQuery(document).ready(function () {
    Dashboard.init();
});
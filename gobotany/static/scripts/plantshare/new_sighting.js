define([
    'bridge/jquery', 
    'bridge/jquery.form',
    'plantshare/upload_modal',
    'mapping/geocoder',
    'util/shadowbox_init'
], function ($, jqueryForm, upload_modal, Geocoder, Shadowbox) {

    var UPLOAD_SPINNER = '/static/images/icons/preloaders-dot-net-lg.gif';
    var DELETE_ICON = '/static/images/icons/close.png';

    $(document).ready(function () {

        function add_new_thumb(thumb_url, full_url, id) {
            // Set the last image's URL, which should be the spinner,
            // to the real image URL.
            var $last_image = $('.thumb-gallery img.thumb').last();
            $last_image.attr('src', thumb_url);
            $last_image.wrap('<a href="' + full_url +
                '" class="preview"></a>');
            $last_image.parent().after('<div class="delete-link"><a href="' +
                id + '"><img src="' + DELETE_ICON + '" /> Remove</a></div>');

            Shadowbox.setup('a.preview');
        }

        function remove_thumb(id, $frame) {
            console.log('Remove thumb ' + id);

            var reject_url = '/plantshare/api/image-reject/' + id;
            $.ajax(reject_url).done(function (data) {
                if(data.success) {
                    $('#sighting-photos').find('input[value=' + id +
                        ']').remove();
                    $frame.fadeOut(300, function () { $frame.remove(); });
                } else {
                    console.log('Error removing sighting photo.');
                }
            });
        }

        function attach_sighting_photo(new_photo_id) {
            $('.template-photo').clone().removeClass('template-photo').attr({
                    'name': 'sightings_photos',
                    'value': new_photo_id
                }).appendTo('#sighting-photos');
        }

        function start_upload() {
            // Add the spinner to the gallery
            $('.thumb-gallery').append(
                '<div class="thumb-frame"><img class="thumb" src="' + 
                UPLOAD_SPINNER + '"></div>');
        }

        function photo_uploaded(info) {
            console.log('Successfully uploaded sighting photo.');
            console.log('New Photo [id=' + info.id + ', thumb=' +
                        info.thumb + ', url=' + info.url + ']');
            add_new_thumb(info.thumb, info.url, info.id);
            attach_sighting_photo(info.id);
            if ((info.latitude !== null) && (info.longitude !== null)) {
                var $location = $('#id_location');
                $location.val(info.latitude + ', ' + info.longitude);
                $location.trigger('blur');   // trigger map update
            }
        }

        function upload_error(errorInfo) {
            console.log('Error: ' + errorInfo);
        }

        $('.delete-link a').live('click', function () {
            $this = $(this);
            console.log('Delete image');
            $frame = $('.thumb-gallery .thumb-frame').has($this);
            removeThumb($this.attr('href'), $frame);

            return false;
        });

        upload_modal.setup('.image-modal', '#upload-link', {
            onStartUpload: start_upload,
            onUploadComplete: photo_uploaded,
            onError: upload_error,
        });
    });

    function get_offset_coordinate(coordinate) {
        // "Offset" a coordinate by a random minimum-to-maximum amount
        // in either direction, in order to be able to produce map
        // markers that avoid fully overlapping so can each be accessed.
        var DEC_PLACES = 6;
        var MIN_DEC_DEGREES = 0.0001; // approx. 25 ft. min. to keep markers
                                      // from bunching up at center
        var MAX_DEC_DEGREES = 0.002;  // approx. 500 ft. max.

        var offset = (Math.random() *
            MAX_DEC_DEGREES + MIN_DEC_DEGREES).toFixed(DEC_PLACES);
        var plus_or_minus = Math.random() < 0.5 ? -1 : 1;
        offset = offset * plus_or_minus;
        var offset_coordinate = (coordinate + offset).toFixed(DEC_PLACES);

        return offset_coordinate;
    }

    function update_latitude_longitude(location, geocoder) {
        // Geocode the location unless it already looks like a pair of
        // coordinates.
        var lat_long_regex = new RegExp(
            '(^(-?(\\d{1,3}.?\\d{1,6}? ?[nNsS]?))([, ]+)' +
            '(-?(\\d{1,3}.?\\d{1,6}? ?[wWeE]?))$)');
        var latitude, longitude = '';
        if (lat_long_regex.test(location)) {
            // TODO: handle more advanced lat/long formats (this
            // currently only handles floats)
            var coordinates = location.replace(' ', '').split(',');
            latitude = coordinates[0];
            longitude = coordinates[1];
            $('#id_latitude').val(latitude);
            $('#id_longitude').val(longitude);
        }
        else {
            geocoder.geocode(location, function (results, status) {
                var lat_lng = geocoder.handle_response(results, status);
                latitude = lat_lng.lat();
                longitude = lat_lng.lng();
                // Offset the coordinates slightly to avoid marker overlap.
                var offset_latitude = get_offset_coordinate(latitude);
                var offset_longitude = get_offset_coordinate(longitude);
                $('#id_latitude').val(offset_latitude);
                $('#id_longitude').val(offset_longitude);
            });
        }
    }

    function enable_disable_submit_button(allow_enable /* optional */) {
        // Enable or disable the submit ("Post Sighting") button.
        var DISABLED = 'disabled';
        var $button = $('.post-sighting-btn');
        var enable = ($('#id_identification').val() !== '' &&
                      $('#id_location').val() !== '');
        var allow_enable = (typeof allow_enable === 'undefined') ?
            true : allow_enable;
        if (enable === true && allow_enable === true) {
            $button = $button.removeClass(DISABLED);
            $button.removeAttr(DISABLED);
        }
        else if (enable === false) {
            $button.addClass(DISABLED);
            $button.prop(DISABLED, true);
        }
    }

    function set_visibility_restriction(is_restricted, is_flagged, is_unknown,
            state, show_dialog) {
        var has_state = (state !== undefined && state !== null &&
                         state !== '');
        var show_dialog = (show_dialog === false) ? false : true;
        if (is_restricted) {
            // Show messages and restrict visibility options.
            $('.restricted').removeClass('hidden');
            $('#id_visibility').val('PRIVATE');
            $('#id_visibility option').each(function () {
                if ($(this).val() !== 'PRIVATE') {
                    $(this).attr('disabled', true);
                }
            });
            if (show_dialog) {
                // Show a dialog with details about the restriction.
                
                var intro, details;
                if (is_unknown) {
                    intro = 'You have found a plant that <b>does not ' +
                        'appear to be in our database</b>.';
                    details = 'This sighting <b>will be not be able to ' +
                        'be made publicly visible</b> until we review it.';
                }
                else {
                    intro = 'Congratulations! You have found a plant that ' +
                        'is <b>rare in ';
                    intro += (has_state) ? state : 'New England';
                    intro += '</b>.';
                    details = 'To protect the plant, this sighting ' +
                        '<b>will not be publicly visible.</b>' +
                        ' A botanist may contact you.';
                }
                var html = '<div class="restricted-dialog">' +
                    '<p>' + intro + '</p>' +
                    '<p>' + details + '</p>' +
                    '<div class="ok"><a class="orange-button" ' +
                    'onclick="Shadowbox.close()">OK</a></div>' +
                    '</div>';
                Shadowbox.open({
                    content: html,
                    player: 'html',
                    title: '',
                    height: 400,
                    width: 320
                });

                // Reset the hidden "approved" field so that upon a
                // significant change to a sighting, new approval will be
                // needed. Reset this only after showing the dialog, which
                // means that the plant or location was edited.
                $('#id_approved').val('False');
            }
        }
        else {
            // Hide messages and unrestrict visibility options.
            $('.restricted').addClass('hidden');
            $('#id_visibility option').each(function () {
                if ($(this).val() !== 'PRIVATE') {
                    $(this).attr('disabled', false);
                }
            });

            // On a new sighting, automatically set the visibility back to
            // its default. Skip this when editing a sighting so as to
            // not be tricky with data that the user already saved.
            if (window.location.href.indexOf('/new/') > -1) {
                $('#id_visibility').val('PUBLIC');
            }

            // Reset the hidden "approved" field: admin. review is not needed.
            $('#id_approved').val('False');
        }

        if (is_flagged) {
            // Set the hidden "flagged" field to mark for admin. review.
            $('#id_flagged').val('True');            
        }
        else {
            $('#id_flagged').val('False');
        }

        enable_disable_submit_button();
    }

    function check_restrictions(plant_name, location, show_dialog) {
        var is_restricted = false;
        var url = '/plantshare/api/restrictions/';
        url += '?plant=' + encodeURIComponent(plant_name) + '&location=' +
            encodeURIComponent(location);
        $.ajax({
            url: url
        }).done(function (json) {
            var is_restricted = false;
            var is_flagged = false;
            var is_unknown = false;
            var state = '';

            if (json.length > 0) {
                // If any result says that sightings are restricted,
                // consider sightings restricted for this plant. (Multiple
                // results are for supporting common names, where the same
                // name can apply to more than one plant.)
                $.each(json, function (i, taxon) {
                    if (taxon.sightings_restricted === true) {
                        is_restricted = true;
                        if (taxon.sightings_flagged === true) {
                            is_flagged = true;
                        }
                        state = taxon.covered_state;
                        return false;   // break out of the loop
                    }
                });
                // As above, if any result says that sightings are flagged,
                // consider sightings flagged for this plant.
                $.each(json, function(i, taxon) {
                    if (taxon.sightings_flagged === true) {
                        is_flagged = true;
                        return false;   // break out of the loop
                    }
                });
            }
            else {
                // The plant sighted did not be match any in the database.
                // Restrict the sighting to private and flag it for
                // admin. review.
                is_restricted = true;
                is_flagged = true;
                is_unknown = true;
            }

            set_visibility_restriction(is_restricted, is_flagged, is_unknown,
                state, show_dialog);
        });
    }

    function clear_restrictions() {
        var is_restricted = false;
        var is_flagged = false;
        var is_unknown = false;
        var state = '';
        set_visibility_restriction(is_restricted, is_flagged, is_unknown,
            state);
    }

    $(window).load(function () {   
        var geocoder = new Geocoder(); // geocoder must be created at onload
        var $identification_box = $('#id_identification');
        var $location_box = $('#id_location');
        
        var initial_identification = $identification_box.val();
        var initial_location = $location_box.val();

        // Check the conservation status for any initial identification
        // value and location value.
        if (initial_identification !== '' && initial_location !== '') {
            var show_dialog = false;
            check_restrictions(initial_identification, initial_location,
                               show_dialog);
        }

        // When the user enters a plant name in the identification
        // field, check the name and location to see if there are
        // conservation concerns. If so, the sighting will be private.
        $identification_box.on('blur', function () {
            enable_disable_submit_button();
            var identification = $(this).val();
            var location = $location_box.val();
            if (location !== '') {
                var show_dialog = true;
                if (identification === initial_identification) {
                    show_dialog = false;
                }
                check_restrictions(identification, location, show_dialog);
            }
            if (identification !== '') {
                initial_identification = identification;
            }
        });
        $identification_box.on('keyup', function (event) {
            // Disable the submit button when the box is cleared, but
            // do not automatically enable it when just typing a letter
            // or two: let a blur event trigger a restrictions check
            // which will then enable the button.
            var allow_enable = false;
            enable_disable_submit_button(allow_enable);

            if ($(this).val() === '') {
                // ID box is empty, so clear any restriction message.
                clear_restrictions();
            }
            else if (event.which == 13) {   // Enter key
                if ($location_box.val() !== '') {
                    check_restrictions($(this).val(), $location_box.val());
                }
            }
        });

        // When the user enters a location, geocode it again if needed,
        // and let the map update.
        $location_box.on('blur', function () {
            enable_disable_submit_button();
            var location = $(this).val();
            if (location !== '') {
                var show_dialog = true;
                if (location === initial_location) {
                    // Location has not changed, so no need to geocode now.
                    show_dialog = false;
                }
                else {
                    // Location has changed: geocode it if necessary.
                    update_latitude_longitude(location, geocoder);
                }

                // Check visibility restrictions for the plant and location.
                check_restrictions($identification_box.val(), location,
                                   show_dialog);
                initial_location = location;
            }
            else {
                // Location box is empty, so clear any restriction message.
                clear_restrictions();
                enable_disable_submit_button(false);
            }
        });
        $location_box.on('keypress keyup', function (event) {
            // Disable the submit button when the box is cleared, but
            // do not automatically enable it when just typing a letter
            // or two: let a blur event trigger a restrictions check
            // which will then enable the button.
            var allow_enable = false;
            enable_disable_submit_button(allow_enable);

            if (event.which === 13) {   // Enter key
                // If the location field is not empty, prevent the form
                // auto-submit so the user can see the map location update.
                // The location field, with its associated map, is similar to
                // textarea in the sense that Enter is used to accomplish
                // something within (or in this case, related to) it.
                var value = $(this).val();
                if (value !== '') {
                    event.preventDefault();
                    update_latitude_longitude(value, geocoder);

                    // Check visibility restrictions for the plant and
                    // location.
                    check_restrictions($identification_box.val(),
                                       $(this).val());
                    return false;
                }
            }
        });

        // Wait a bit for the location map to update upon submitting.
        $('#main form').submit(function (event) {
            event.preventDefault();
            var form = this;
            var seconds = 1;                      
            setTimeout(function () {
                form.submit();
            }, seconds * 1000);
        });
    });

});

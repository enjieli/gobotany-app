/* RequireJS Build profile for production deployment to Heroku instance */
({
    appDir: '../../gobotany/static/scripts',
    dir: 'build',
    baseUrl: '.',
    mainConfigFile: '../../gobotany/static/scripts/require_config.js',

    findNestedDependencies: true,
    removeCombined: true,
    preserveLicenseComments: false,

    modules: [
        {
            name: 'gobotany.application',
            include: [
                'lib/require',

                'dkey/dkey',
                'editor/cv',
                'mapping/google_maps',
                'mapping/sightings_map',
                'plantshare/myprofile',
                'plantshare/plantshare',
                'plantshare/registration_complete',
                'plantshare/sightings_locator',
                'plantshare/sightings',
                'plantshare/sign_up',
                'plantshare/new_sighting',
                'simplekey/simple',
                'simplekey/results',
                'taxa/species',
                'taxa/family',
                'taxa/genus',
                'site/help',
                'site/advanced_map',
                'site/glossary',
                'site/species_list',
                'site/home',
                'site/maps_test',
                'util/activate_search_suggest',
                'util/suggester_init',
                'util/location_field_init'
            ],
            create: true
        }
    ]
})

// New Dojo 1.7 global configuration object
// This must be loaded before the dojo AMD loader
dojoConfig = {
    isDebug: false,
    baseUrl: '/static/scripts',
    tlmSiblingOfDojo: false,
    async: false,
    locale: 'en-us',
    packages: [
        { name: 'dojo', location: 'lib/dojo' },
        { name: 'dojox', location: 'lib/dojox' },
        { name: 'dijit', location: 'lib/dijit' },
        { name: 'jquery', location: 'lib/jquery' },
        { name: 'tools', location: 'lib/tools' },
        { name: 'gobotany', location: '../gobotany' },
        { name: 'simplekey', location: 'simplekey' },
        { name: 'bridge', location: 'bridge' },
        { name: 'util', location: 'util' }
    ],
    // Until we fix the rest of the AMD modules
    // we need to leave this as true
    parseOnLoad: true
};


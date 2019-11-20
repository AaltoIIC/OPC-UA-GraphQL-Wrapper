// Populate example JSON data from OPC UA server on page load
// Toggle hide function for document methods

$(function() {
    "use strict";

    $.get( $( "#GetValueLink" ).attr( 'href' ), function ( response ) {
        $( "#GetValueCode" ).html( "<br>" + JSON.stringify( response, null, 2) );
    });

    $.get( $( "#GetObjectsLink" ).attr( 'href' ), function ( response ) {
        $( "#GetObjectsCode" ).html( "<br>" + JSON.stringify( response, null, 2) );
    });

    $.get( $( "#PutValueLink" ).attr( 'href' ), function ( response ) {
        delete response[ "data" ][ "dataType" ]; 
        $( "#PutValueCode" ).html( "<br>" + JSON.stringify( response, null, 2) );
    });

    $( ".method" ).siblings().hide();

    $( ".method" ).click( function() {
        $( this ).siblings().toggle();
    });

});
// Function to browse nodes (folders) of OPC UA server from a web page.
// Each click on node causes the function to retrieve from the server 
// subnodes of a node or value of the node.
// Also constructs copyable node arguments and example queries to last
// selected node for convenience.

$(function() {
    "use strict";

    $(document).on( "click", ".object", function (event) {
        
        event.preventDefault();
        const targetUrl = $(this).attr("href");
        const origin = location.origin;
        const thisColumn = $(this).parent().attr("id");

        // Change link colors based on selection
        $(this).css("background-color", "darkcyan");
        $(this).siblings("a").css("background-color", "silver");

        // Ajax GET for retrieving value or subnodes of clicked node
        let appendix = "";
        let server = targetUrl.split("/")[3];
        let nodeId = targetUrl.split("/")[4];
        if (nodeId === undefined) {
            nodeId = "";
        }
        let query = `
            query{
                node(server: "${server}", nodeId: "${nodeId}") {
                    variable{value dataType} subNodes{name nodeId server}
                }
            }
        `;

        // Request performance measurement start time
        let requestTime = performance.now();

        $.post({
            url: origin + "/graphql",
            headers: {
                "Content-Type": "application/json"
                //"X-CSRFToken": csrf_token
            },
            data: JSON.stringify({query}),
            success: function(response) {

                // Request performance measurement end time and logging result to console
                requestTime = (performance.now() - requestTime);
                console.log("Request took " + requestTime.toFixed(2) + " ms");

                // Construct an element depending on what property is returned
                if (response.data.node.variable !== null) {
                    if (response.data.node.variable.value !== null) {
                        let printOut = {"variable": response.data.node.variable};
                        appendix = "<pre><code class = 'value'>" + JSON.stringify(printOut, null, 2) + "</code></pre>";
                    }
                }
                if (response.data.node.subNodes != null) {
                    for (let subNode of response.data.node.subNodes) {
                        if (subNode !== null) {
                            const name = subNode.name;
                            const targetUrl = origin + "/" + subNode.server + "/" + subNode.nodeId;
                            appendix = appendix.concat(
                                "<a class = 'object' href = ", targetUrl, ">", name, "</a>"
                                );
                        }
                    }
                }
                if (response.hasOwnProperty("errors")) {
                    for (let error of response.errors) {
                        if (!error.path.includes("variable")) {
                            appendix = appendix.concat(
                                "<span class = 'value error'>" + error.message + "</span>"
                            );
                        }
                    }
                }

                // Remove columns of nodes that are deeper than clicked node
                const column = 'Column_' + (parseInt(thisColumn.split("_").pop()) + 1);
                $("#" + column).nextAll().addBack().remove();

                // Update arguments to correspond latest node click
                $(".TargetServer").text('"' + server + '"');
                $(".TargetNode").text('"' + nodeId + '"');

                // Append constructed element to NodeRow
                $("#NodeRow").append(
                    "<td id = " + column + " class = 'column'>" + appendix + "</td>"
                );
            },
            error: function(response) {
                console.log(response);
                if (response.responseJSON.errors.length > 0) {
                    for (let error of response.responseJSON.errors) {
                        appendix = appendix.concat(
                            "<span class = 'value error'>" + error.message + "</span>"
                        );
                    }
                } else {
                    let error = "Connection failed to API server";
                    appendix = "<span class = 'value error'>" + error + "</span>";
                }

                // Remove columns of nodes that are deeper than clicked node
                const column = 'Column_' + (parseInt(thisColumn.split("_").pop()) + 1);
                $("#" + column).nextAll().addBack().remove();

                // Update arguments to correspond latest node click
                $("#TargetServer").text('"' + server + '"');
                $("#TargetNode").text('"' + nodeId + '"');

                $("#NodeRow").append(
                    "<td id = " + column + " class = 'column'>" + appendix + "</td>"
                );
            }
        });
    });
});
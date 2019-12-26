<!DOCTYPE html>
<html>
    <head>
        <title>VCU Pro - Info</title>
        <link type="text/css" href="styles.css" rel="stylesheet">
    </head>

    <body>
        <h1>VCU System Information</h1>

        <table>
        <tr>
            <th>Name</th>
            <th>Value</th>
        </tr>

        %for entry in data:
        <tr>
            <td style="width:25%">{{entry.header}}</td>
            <td style="width:75%">{{!entry.text}}</td>
        </tr>
        %end

        </table>

        <p></p>

<!--
        <form action="/info" method="GET">
            <button class="button" type="submit" name="method" value="refresh">Refresh</button>
        </form>
-->
        <button class="button" onClick="window.location.reload();">Refresh Page</button>
        <p></p>
        <form action="/action" method="POST">
            <button class="button" type="submit" name="method" value="signal-query">Enable Signal Measurement</button>
        </form>
    </body>


%if message:
    <p>Status: {{message}}</p>
%end

</html>

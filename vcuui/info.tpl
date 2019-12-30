<!DOCTYPE html>
<html>

<head>
    <title>VCU Pro</title>
    <link type="text/css" href="styles.css" rel="stylesheet">
</head>

<body>
    <div class="sidenav">
        <div class="btn-group">
            <button class="button" onClick="window.location.href = '/'">Refresh Page</button>
            <p></p>
            <button id="button_location" class="button button_green" type="button" onclick="do_location()">Enable Location</button>
            <button id="button_signal" class="button button_green" type="button" onclick="do_signal()">Enable Signal Meas.</button>
            <button id="button_ping" class="button button_green" type="button" onclick="do_ping()">Ping</button>
            <p></p>
            <button id="button_location" class="button button_orange" type="button" onclick="do_modem_reset()">Reset Modem</button>
            <button id="button_location" class="button button_orange" type="button" onclick="xxx()">Reboot System</button>

            <p>Version: v{{version}}</p>
        </div>
    </div>

    <div class="main">
        <h1>VCU System Information</h1>
        <table>
            %for entry in data:
            <tr>
                <td style="width:25%">{{entry.header}}</td>
                <td style="width:75%">{{!entry.text}}</td>
            </tr>
            %end

        </table>

        %if message:
        <p>Status: {{message}}</p>
        %end

        <!-- The Modal -->
        <div id="myModal" class="modal">
            <!-- Modal content -->
            <div class="modal-content">
                <div class="modal-header">
                    <span class="close">&times;</span>
                    <h2>Information</h2>
                </div>
                <div class="modal-body">
                    <p id=message>Some text in the Modal Body</p>
                    <pre class="terminal" id="console">
                    <!-- room for console output -->
                    </pre>
                </div>
            </div>
        </div>
    </div>
    </div>

    <script>
        function do_ping() {
            console.log("executing do_ping()")

            // Get the modal
            var modal = document.getElementById("myModal");

            // Get the <span> element that closes the modal
            var span = document.getElementsByClassName("close")[0];

            // When the user clicks on <span> (x), close the modal
            span.onclick = function() {
                modal.style.display = "none";
            }

            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("console").innerHTML = this.responseText;
                }
            };

            document.getElementById("message").innerHTML = "Executing ping, please wait ...";
            document.getElementById("console").innerHTML = "";
            document.getElementById("console").style.display = "block";
            modal.style.display = "block";

            xhttp.open("GET", "do_ping", true);
            xhttp.send();
        }

        function do_location() {
            // Get the modal
            var modal = document.getElementById("myModal");

            // Get the <span> element that closes the modal
            var span = document.getElementsByClassName("close")[0];

            // When the user clicks on <span> (x), close the modal
            span.onclick = function() {
                modal.style.display = "none";
            }

            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            document.getElementById("console").style.display = "none";
            document.getElementById("message").innerHTML = "Enabling 3GPP location detection";
            modal.style.display = "block";

            xhttp.open("GET", "do_location", true);
            xhttp.send();
        }

        function do_signal() {
            // Get the modal
            var modal = document.getElementById("myModal");

            // Get the <span> element that closes the modal
            var span = document.getElementsByClassName("close")[0];

            // When the user clicks on <span> (x), close the modal
            span.onclick = function() {
                modal.style.display = "none";
            }

            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            document.getElementById("console").style.display = "none";
            document.getElementById("message").innerHTML = "Enabling signal quality measurements";
            modal.style.display = "block";

            xhttp.open("GET", "do_signal", true);
            xhttp.send();
        }

        function do_modem_reset() {
            res = confirm("Do you really want to reset the GSM modem?");
            if (res == false) {
                return
            }

            // Get the modal
            var modal = document.getElementById("myModal");

            // Get the <span> element that closes the modal
            var span = document.getElementsByClassName("close")[0];

            // When the user clicks on <span> (x), close the modal
            span.onclick = function() {
                modal.style.display = "none";
            }

            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            document.getElementById("console").style.display = "none";
            document.getElementById("message").innerHTML = "Resetting modem";
            modal.style.display = "block";

            xhttp.open("GET", "do_modem_reset", true);
            xhttp.send();
        }
    </script>
</body>

</html>
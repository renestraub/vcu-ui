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
            <button id="button_xxx" class="button button_green" type="button" onclick="do_cell_find()">Find Cell</button>
            <p></p>
            <button id="button_xxx" class="button button_orange" type="button" onclick="do_store_gnss()">Save GNSS State</button>
            <button id="button_location" class="button button_orange" type="button" onclick="do_sertonet()">uCenter ser2net</button>
            <button id="button_location" class="button button_orange" type="button" onclick="do_modem_reset()">Reset Modem</button>
            <button id="button_location" class="button button_red" type="button" onclick="alert('not yet implemented')">Reboot System</button>

            <p>Version: {{version}}</p>
        </div>
    </div>

    <div class="main">
        <h1>VCU System Information</h1>
        <table>
            %for entry in table:
            <tr>
<!--                <td style="width:25%">{{entry.header}}</td>
                <td style="width:75%">{{!entry.text}}</td> -->
                <td>{{entry.header}}</td>
                <td>{{!entry.text}}</td>
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

    <div class="footer">
        <p>
            Disclaimer: This tool is a private project, not affiliated with NetModule AG.
            The project is provided under the MIT license.
        </p>
    </div>

    <script>
        // data provided to web page
        %for key, value in data.items():
            localStorage.{{key}} = {{value}};
        %end

        // Get the modal
        var modal = document.getElementById("myModal");
        // Get the <span> element that closes the modal
        var span = document.getElementsByClassName("close")[0];
        // When the user clicks on <span> (x), close the modal
        span.onclick = function() {
            modal.style.display = "none";
        }

        function model_open(message) {
            document.getElementById("message").innerHTML = message;
            document.getElementById("console").innerHTML = "";
            document.getElementById("console").style.display = "none";
            modal.style.display = "block";
        }

        function do_ping() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    // show console and display ping result
                    document.getElementById("console").style.display = "block";
                    document.getElementById("console").innerHTML = this.responseText;
                }
            };

            model_open('Executing ping, please wait ...');

            xhttp.open("GET", "do_ping", true);
            xhttp.send();
        }

        function do_location() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            model_open('Enabling 3GPP location detection');

            xhttp.open("GET", "do_location", true);
            xhttp.send();
        }

        function do_signal() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            model_open('Enabling signal quality measurements');

            xhttp.open("GET", "do_signal", true);
            xhttp.send();
        }

        function do_modem_reset() {
            res = confirm("Do you really want to reset the GSM modem?");
            if (res == false) {
                return
            }

            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            model_open('Resetting modem');

            xhttp.open("GET", "do_modem_reset", true);
            xhttp.send();
        }

        function do_cell_find() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            model_open('Trying to locate cell');

            mcc = localStorage.mcc
            mnc = localStorage.mnc
            lac = localStorage.lac
            cid = localStorage.cid
            query = `mcc=${mcc}&mnc=${mnc}&lac=${lac}&cid=${cid}`;
            uri = "/do_cell_locate?" + encodeURI(query)
            xhttp.open("GET", uri, true);
            xhttp.send();
        }        

        function do_sertonet() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            model_open('Setting up system for uCenter connection');

            xhttp.open("GET", "do_ser2net", true);
            xhttp.send();
        }

        function do_store_gnss() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    document.getElementById("message").innerHTML += "<br>" + this.responseText
                }
            };

            model_open('Saving GNSS State');

            xhttp.open("GET", "do_store_gnss", true);
            xhttp.send();
        }
    </script>
</body>

</html>
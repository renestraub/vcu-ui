<!DOCTYPE html>
<html>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<head>
    <title>VCU Pro</title>
    <link type="text/css" href="styles.css" rel="stylesheet">
</head>

<body>
    <h1>{{title}}</h1>

    <div style="overflow:auto">
        <div class="menu">
            <div class="btn-group">
                <button class="button" onClick="window.location.href = '/gnss'">Refresh Page</button>
                <p></p>
                <button id="button_ser2net" class="button button_orange" type="button" onclick="do_sertonet()">uCenter ser2net</button>
                <p></p>
                <button id="button_configure" class="button button_orange" type="button" onclick="do_gnss_config()">Configure</button>
                <p></p>
                <button id="button_gnss_save" class="button button_green" type="button" onclick="do_store_gnss()">Save GNSS State</button>
                <button id="button_configure" class="button button_orange" type="button" onclick="do_gnss_coldstart()">Cold Start</button>
            </div>
            <p>Version: {{version}}</p>
        </div>

        <div class="main">
            <table>
                %if table:
                    %for entry in table:
                    <tr>
                        <td>{{entry.header}}</td>
                        <td>{{!entry.text}}</td>
                    </tr>
                    %end
                %end
            </table>

            <p></p>

            <table>
                <tr>
                    <th>Configuration</th>
                </tr>
                <tr>
                    <td>Dynamic Model</td>
                    <td>
                        <select id="dyn_model">
                            <option value="0">0: Portable</option>
                            <option value="2">2: Stationary</option>
                            <option value="3">3: Pedestrian</option>
                            <option value="4">4: Automotive</option>
                            <option value="5">5: Sea</option>
                        </select>
                    </td>
                </tr>
                <tr>
                    <td>NMEA Protocol</td>
                    <td>{{data['nmea_protocol']}}</td>
                </tr>
            </table>

            %if message:
            <p>Status: {{message}}</p>
            %end

            <!-- The Modal Dialog -->
            <div id="myModal" class="modal">
                <!-- Modal content -->
                <div id="myDialog" class="modal-content">
                    <div id="myTimerBar" class="modal-timer-bar"></div>
                    <div class="modal-header">
                        <span id="myCloseButton" class="close">&times;</span>
                        <h2>Information</h2>
                    </div>
                    <div class="modal-body">
                        <p id=message></p>
                        <pre class="terminal" id="console">
                        <!-- room for console output -->
                        </pre>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <br><br><br>
    <div class="footer">
        <p>
            Disclaimer: This tool is a private project, not affiliated with NetModule AG.
            The project is provided under the MIT license.
        </p>
    </div>

    <script>
        // data provided to web page
        %if data:
            %for key, value in data.items():
                localStorage.{{key}} = {{value}};
            %end
        %end

        // Set UI configuration items with values provided by system
        console.log(`system dyn_model is {{data['dyn_model']}}`)
        console.log(`system nmea is {{data['nmea_protocol']}}`)

        document.getElementById("dyn_model").value = "{{data['dyn_model']}}";

        var timer_close = null;

        // Get the modal elements
        var modal = document.getElementById("myModal");
        var dialog = document.getElementById("myDialog");
        var dialog_message = document.getElementById("message");
        var dialog_console = document.getElementById("console");
        var close_button = document.getElementById("myCloseButton");
        var timer_bar = document.getElementById("myTimerBar");
        
        // When the user clicks on <span> (x), close the modal
        close_button.onclick = function() {
            modal_close();
        }

        // When the user clicks in the dialog stop the auto timer
        dialog.onclick = function() {
            stop_close_timer();
        }

        function model_open(message) {
            modal.style.display = "block";
            dialog_message.innerHTML = message;
            dialog_console.innerHTML = "";
            dialog_console.style.display = "none";
            timer_bar.style.display = "none";
        }

        function modal_close() {
            stop_close_timer();
            modal.style.display = "none";

            // check if this is safe
            location.reload();
        }

        function modal_enable_close_timer() {
            timer_bar.style.display = "block";
            timer_bar.setAttribute("class", "modal-timer-bar");
        }

        function start_close_timer(secs) {
            timer_bar.setAttribute("class", "modal-timer-bar-active");
            timer_bar.style.transition = `width ${secs}s linear`;
            timer_close = setTimeout(timer_modal_close, secs*1000);
        }

        function stop_close_timer() {
            timer_bar.style.transition = "width 1s linear";
            timer_bar.setAttribute("class", "modal-timer-bar");
            if (timer_close != null) {
                console.log("stopping timer");
                clearTimeout(timer_close);
                timer_close = null;
            }
        }

        function timer_modal_close() {
            console.log("timer elapsed");
            modal_close();
        }

        /* Actions */

        function do_sertonet() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(3);
                }
            };

            model_open('Setting up system for uCenter connection');
            modal_enable_close_timer();

            xhttp.open("GET", "do_ser2net", true);
            xhttp.send();
        }

        function do_store_gnss() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(5);
                }
            };

            model_open('Saving GNSS State');
            modal_enable_close_timer();

            xhttp.open("GET", "do_store_gnss", true);
            xhttp.send();
        }

        function do_gnss_config() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(2);
                }
            };

            model_open('Configuring GNSS');
            modal_enable_close_timer();

            var dyn_model = document.getElementById("dyn_model").value; 
            console.log(`new dyn_model is ${dyn_model}`)

            query = `dyn_model=${dyn_model}`;
            uri = "/do_gnss_config?" + encodeURI(query);

            xhttp.open("GET", uri, true);
            xhttp.send();
        }

        function do_gnss_coldstart() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(2);
                }
            };

            model_open('Performing GNSS coldstart');
            modal_enable_close_timer();

            xhttp.open("GET", "do_gnss_coldstart", true);
            xhttp.send();
        }
    </script>
</body>

</html>
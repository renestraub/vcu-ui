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
                <button class="button" onClick="window.location.href = '/'">Home</button>
                <p></p>
                <button id="button_ser2net" class="button button_orange" type="button" onclick="do_sertonet()">uCenter ser2net</button>
                <p></p>
                <button id="button_state_save" class="button button_green" type="button" onclick="do_state_save()">Save GNSS State</button>
                <button id="button_state_clear" class="button button_green" type="button" onclick="do_state_clear()">[Clear GNSS State]</button>
                <button id="button_col_start" class="button button_orange" type="button" onclick="do_gnss_coldstart()">Cold Start</button>
                <p></p>
                <button class="button" onClick="window.location.href = '/gnss'">Refresh Page</button>
            </div>
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
                    <td class="td_notyet">UART Bitrate</td>
                    <td>9600|115200</td>
                </tr>
                <tr>
                    <td>NMEA Protocol</td>
                    <td>{{data['nmea_protocol']}}</td>
                </tr>
                <tr>
                    <td class="td_notyet">ESF Status</td>
                    <td></td>
                </tr>
                <tr>
                    <td class="td_notyet">Auto Alignment</td>
                    <td>On/Off</td>
                </tr>
                <tr>
                    <td class="td_notyet">Alignment Status</td>
                    <td>xxx/Coarse/Fine fkdjsljf dklsfjlksdjflkdsöjfdslkö</td>
                </tr>
                <tr>
                    <td class="td_notyet">Mounting Roll</td>
                    <td>1.23 deg</td>
                </tr>
                <tr>
                    <td class="td_notyet">Mounting Pitch</td>
                    <td>1.23 deg</td>
                </tr>
                <tr>
                    <td class="td_notyet">Mounting Yaw</td>
                    <td>1.23 deg</td>
                </tr>
            </table>

            <p></p>

            <table>
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
                    <td class="td_notyet">Automatic Alignment</td>
                    <td>
                        <select id="auto_imu_align">
                            <option value="on">On</option>
                            <option value="off">Off</option>
                        </select>
                    </td>
                </tr>
                <tr>
                    <td class="td_notyet">VRP-Antenna</td>
                    <td>
                        X: <input type="number" id="vrp-ant-x" class="input_vrp" min="-5.0" max="5.0" step="0.01">
                        Y: <input type="number" id="vrp-ant-y" class="input_vrp" min="-5.0" max="5.0" step="0.01">
                        Z: <input type="number" id="vrp-ant-z" class="input_vrp" min="-5.0" max="5.0" step="0.01">
                    </td>
                </tr>
                <tr>
                    <td class="td_notyet">VRP-IMU</td>
                    <td>
                        X: <input type="number" id="vrp-imu-x" class="input_vrp" min="-5.0" max="5.0" step="0.01">
                        Y: <input type="number" id="vrp-imu-y" class="input_vrp" min="-5.0" max="5.0" step="0.01">
                        Z: <input type="number" id="vrp-imu-z" class="input_vrp" min="-5.0" max="5.0" step="0.01">
                    </td>
                </tr>
                <tr>
                    <td colspan="2">
                        <button id="button_configure" class="button button_orange" type="button" onclick="do_gnss_config()">Configure</button>
                    </td>
                </tr>
            </table>

            %if message:
            <p>Status: {{message}}</p>
            %end

            <br><br>

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

    % include('footer.tpl')

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

        function do_state_save() {
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
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
                <button class="button" onClick="window.location.href = '/gnss'">GNSS Page</button>
                <p></p>
                <button id="button_location" class="button button_green" type="button" onclick="do_location()">Enable Location</button>
                <button id="button_signal" class="button button_green" type="button" onclick="do_signal()">Enable Signal Meas.</button>
                <button id="button_ping" class="button button_green" type="button" onclick="do_ping()">Ping</button>
                <button id="button_find_cell" class="button button_green" type="button" onclick="do_cell_find()">Find Cell</button>
                <p></p>
                %if not cloud_log:
                    <button id="button_cloud" class="button button_orange" type="button" onclick="do_cloud(true)">Start Cloud Logging</button>
                %else:
                    <button id="button_cloud" class="button button_green" type="button" onclick="do_cloud(false)">Stop Cloud Logging</button>
                %end
                <p></p>
                <button id="button_modem_reset" class="button button_orange" type="button" onclick="do_modem_reset()">Reset GSM Modem</button>
                <button id="button_reboot" class="button button_red" type="button" onclick="alert('not yet implemented')">Reboot System</button>
                <p></p>
                <button class="button button_slider" onClick="window.location.href = '/'">Refresh Page</button>
                <label class="switch">
                    <input id="checkbox_auto_refresh" type="checkbox" onclick="do_auto_refresh(this)">
                    <span class="slider round"></span>
                </label>
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

        var timer_close = null;
        var timer_refresh = null;
        var checkbox_auto_refresh = document.getElementById("checkbox_auto_refresh");

        // Get the modal
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

        console.log("page loading")
        console.log(`refresh: ${localStorage.refresh}`)

        if (localStorage.refresh == "on") {
            console.log("restart refresh timer");
            checkbox_auto_refresh.checked = true;
            do_auto_refresh(checkbox_auto_refresh)
        }

        function do_auto_refresh(elem) {
            // console.log("refresh toggle")
            // console.log(`${elem.checked}`)

            if (elem.checked) {
                localStorage.refresh = "on";
                timer_refresh = setTimeout(function() {
                    console.log("reloading page");
                    location.reload();
                }, 2000);
            }
            else {
                localStorage.refresh = "off";
                clearInterval(timer_refresh)
                timer_refresh == null
            }
        }

        function do_ping() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    // show console and display ping result
                    dialog_console.style.display = "block";
                    dialog_console.innerHTML = this.responseText;
                    start_close_timer(10);
                }
            };

            model_open('Executing ping, please wait ...');
            modal_enable_close_timer();

            xhttp.open("GET", "do_ping", true);
            xhttp.send();
        }

        function do_location() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(3);
                }
            };

            model_open('Enabling 3GPP location detection');
            modal_enable_close_timer();

            xhttp.open("GET", "do_location", true);
            xhttp.send();
        }

        function do_signal() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(3);
                }
            };

            model_open('Enabling signal quality measurements');
            modal_enable_close_timer();

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
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(3);
                }
            };

            model_open('Resetting modem');
            modal_enable_close_timer();

            xhttp.open("GET", "do_modem_reset", true);
            xhttp.send();
        }

        function do_cell_find() {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                }
            };

            model_open('Trying to locate cell');

            mcc = localStorage.mcc;
            mnc = localStorage.mnc;
            lac = localStorage.lac;
            cid = localStorage.cid;
            query = `mcc=${mcc}&mnc=${mnc}&lac=${lac}&cid=${cid}`;
            uri = "/do_cell_locate?" + encodeURI(query);
            xhttp.open("GET", uri, true);
            xhttp.send();
        }        

        function do_cloud(enable) {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    dialog_message.innerHTML += "<br>" + this.responseText;
                    start_close_timer(2);
                }
            };

            model_open('Starting cloud logging');
            modal_enable_close_timer();

            if (enable) {
                query = `enable=True`;
            } else { 
                query = `enable=False`;
            }
            uri = "/do_cloud?" + encodeURI(query);
            xhttp.open("GET", uri, true);
            xhttp.send();
        }
    </script>
</body>

</html>
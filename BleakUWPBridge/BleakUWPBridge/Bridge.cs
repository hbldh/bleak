using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Foundation;

namespace BleakBridge
{
    public class Bridge: IDisposable
    {
        public Dictionary<ushort, TypedEventHandler<GattCharacteristic, GattValueChangedEventArgs>> callbacks;
        
        public Bridge()
        {
            callbacks = new Dictionary<ushort, TypedEventHandler<GattCharacteristic, GattValueChangedEventArgs>>();
        }

        public void Dispose()
        {
            callbacks.Clear();
        }

        #region Notifications

        public void AddValueChangedCallback(GattCharacteristic characteristic, TypedEventHandler<GattCharacteristic, GattValueChangedEventArgs> callback)
        {
            this.callbacks[characteristic.AttributeHandle] = callback;
            characteristic.ValueChanged += callback;
        }

        public void RemoveValueChangedCallback(GattCharacteristic characteristic)
        {
            if (this.callbacks.ContainsKey(characteristic.AttributeHandle))
            {
                var stored_callback = this.callbacks[characteristic.AttributeHandle];
                this.callbacks.Remove(characteristic.AttributeHandle);
                characteristic.ValueChanged -= stored_callback;
            }
        }

        #endregion

        /// <summary>
        /// Method is not actually used, merely here to enable the bridge to provide Python.NET access to the Windows namespace.
        /// </summary>
        /// <param name="characteristic">GATTCharacteristic</param>
        /// <returns></returns>
        private async Task<GattCommunicationStatus> DummyMethod(GattCharacteristic characteristic)
        {
            await Task.Delay(1);
            return GattCommunicationStatus.Success;
        }

        
    }
}
